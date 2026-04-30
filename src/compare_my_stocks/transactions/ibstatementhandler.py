"""Importer for the IB Activity Statement CSV.

Generates a synthetic ``buydict`` from the *Open Positions* section
(stocks only) and from the *Realized & Unrealized Performance Summary*
(closed-out stocks treated as Qty=0 sells reflecting L/T realized
profit/loss).

Unlike the IB Flex / MyStocks handlers, this source does not contain
individual trades — only end-of-period state. Each emitted entry is
therefore a synthetic event timestamped at the statement period date.
"""
import csv
import datetime
import logging
from collections import namedtuple

from dateutil import parser as _dateparser

from common.simpleexceptioncontext import simple_exception_handling
from config import config, resolvefile
from transactions.transactionhandler import TrasnasctionHandler
from transactions.transactioninterface import (
    BuyDictItem,
    TransactionHandlerImplementator,
    TransactionSource,
)


def get_ib_statement_handler(man):
    return IBStatementTransactionHandler(man)


# Section header offsets within an "Open Positions" *Data* row, after
# stripping the leading two cells ("Open Positions", "Data"):
#   0 DataDiscriminator, 1 Asset Category, 2 Currency, 3 Symbol,
#   4 Quantity, 5 Mult, 6 Cost Price, 7 Cost Basis, 8 Close Price,
#   9 Value, 10 Unrealized P/L, 11 Code
OpenPosition = namedtuple(
    "OpenPosition",
    "discriminator asset_category currency symbol quantity mult cost_price cost_basis close_price value unrealized_pl code",
)

# Realized & Unrealized rows after stripping the two leading cells:
#   0 Asset Category, 1 Symbol, 2 Cost Adj.,
#   3 Realized S/T Profit, 4 Realized S/T Loss,
#   5 Realized L/T Profit, 6 Realized L/T Loss,
#   7 Realized Total, ...
RealizedRow = namedtuple(
    "RealizedRow",
    "asset_category symbol cost_adj st_profit st_loss lt_profit lt_loss realized_total",
)


def _to_float(s, default=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def parse_ib_statement(path):
    """Parse the CSV at *path* and return ``(period_date, open_positions, realized_rows)``.

    *open_positions* is a list of OpenPosition for stocks only.
    *realized_rows* is a list of RealizedRow for stocks only.
    *period_date* is a ``datetime`` (UTC-naive, midnight) — falls back to today
    if the *Period* field is absent.
    """
    period_date = None
    opens = []
    realized = []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            section = row[0]
            if section == "Statement" and len(row) >= 4 and row[2] == "Period":
                # Period may be a single date or a range "X - Y"; take the last.
                raw = row[3]
                last = raw.split(" - ")[-1].strip()
                try:
                    period_date = _dateparser.parse(last)
                except (ValueError, TypeError):
                    period_date = None
            elif section == "Open Positions" and len(row) >= 3 and row[1] == "Data":
                # Skip Total rows; only consume Data rows.
                payload = row[2:]
                # Pad/truncate to expected width.
                payload = (payload + [""] * 12)[:12]
                op = OpenPosition(*payload)
                if op.asset_category == "Stocks":
                    opens.append(op)
            elif (
                section == "Realized & Unrealized Performance Summary"
                and len(row) >= 3
                and row[1] == "Data"
            ):
                payload = row[2:]
                # Truncate to first 8 fields (we only care about realized + symbol).
                if len(payload) >= 8 and payload[0] == "Stocks" and payload[1]:
                    realized.append(RealizedRow(*payload[:8]))

    if period_date is None:
        period_date = datetime.datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    return period_date, opens, realized


class IBStatementTransactionHandler(TrasnasctionHandler, TransactionHandlerImplementator):
    NAME = "IBStatement"

    def __init__(self, manager):
        super().__init__(manager)

    def save_cache_date(self):
        return 0

    def log_buydict_stats(self):
        if not self._buydic:
            logging.info("IBStatement buy dictionary is empty.")
            return
        logging.info(
            f"IBStatement buy dictionary contains {len(self._buydic)} synthetic entries "
            f"({len(self._buysymbols)} symbols)."
        )

    def populate_buydic(self):
        ok, path = resolvefile(self.SrcFile, use_alternative=config.Running.UseAlterantiveLocation)
        if not ok:
            logging.error(f"SrcFile {self.SrcFile} not found for {self.NAME}")
            return
        logging.info(f"IB statement src file is {path}")
        self.read_statement(path)

    @simple_exception_handling("read_ib_statement")
    def read_statement(self, path):
        period_date, opens, realized = parse_ib_statement(path)

        symbols_with_open = set()
        # Open Positions → one synthetic buy per symbol at the cost basis.
        ts = period_date
        for op in opens:
            symbol = self.translate_symbol(op.symbol)
            qty = _to_float(op.quantity)
            cost = _to_float(op.cost_price)
            if not symbol or qty == 0:
                continue
            dt = self._unique_dt(ts)
            self._buydic[dt] = BuyDictItem(
                qty,
                cost,
                symbol,
                f"IBStatement: open position",
                None,
                TransactionSource.STOCK,
            )
            self._buysymbols.add(symbol)
            symbols_with_open.add(symbol)
            if op.currency:
                self.update_sym_property(symbol, op.currency, "currency")

        # Closed-out stocks: where L/T realized != 0 and symbol is not in Open
        # Positions. Emit a single synthetic sell with Qty=0 carrying the net
        # L/T realized P/L in the Cost field.
        for r in realized:
            symbol = self.translate_symbol(r.symbol)
            if not symbol or symbol in symbols_with_open:
                continue
            lt = _to_float(r.lt_profit) + _to_float(r.lt_loss)
            if lt == 0:
                continue
            dt = self._unique_dt(ts)
            self._buydic[dt] = BuyDictItem(
                0.0,
                lt,
                symbol,
                f"IBStatement: closed L/T realized",
                None,
                TransactionSource.STOCK,
            )
            self._buysymbols.add(symbol)

    def _unique_dt(self, ts):
        dt = ts
        while dt in self._buydic:
            dt = dt + datetime.timedelta(milliseconds=1)
        return dt

    def get_vars_for_cache(self):
        return (self._buydic, self._buysymbols, "tmp")

    def set_vars_for_cache(self, v):
        (self._buydic, self._buysymbols, _) = v
        if not self._buydic:
            return 0
        return 1

    def get_portfolio_stocks(self):
        return self._buysymbols

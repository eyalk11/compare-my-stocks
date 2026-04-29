# Quick Start

A 10‑minute guide to getting **compare-my-stocks** running with your first graph.

> Already installed? Jump to [First launch](#3-first-launch). \
> Want to tune behavior? See [CONFIGURATION.md](CONFIGURATION.md).

---

## 1. Install

### Option A — End user (Windows installer)

1. Grab the latest `.exe` installer from the [Releases](https://github.com/eyalk11/compare-my-stocks/releases) page.
2. Run it. The default install location is fine.
3. Launch from the Start menu, or run `compare-my-stocks.exe --console` from a terminal if you want to see logs.

### Option B — Developer (pip)

Requires Python **3.11**.

```powershell
pip install "compare-my-stocks[full]"
```


After install, recommended to copy the bundled defaults to your data dir so you can edit them:

```powershell
# Windows
xcopy /E /I "<site-packages>\compare_my_stocks\data" "$env:USERPROFILE\.compare_my_stocks\data"
```

```bash
# macOS / Linux
cp -r <site-packages>/compare_my_stocks/data ~/.compare_my_stocks/data
```

The data dir is `~/.compare_my_stocks/` by default. Override it with the
`COMPARE_STOCK_PATH` environment variable.

---

## 2. Pick a market data source

You need **either** Interactive Brokers **or** Polygon. IB is the default and
gets you the most features (live portfolio sync). Polygon is easier if you
just want price history.

### 2a. Interactive Brokers (default)

1. Install and run **Trader Workstation** (TWS) or IB Gateway. Sign in (read-only is fine).
2. In TWS: **Edit → Global Configuration → API → Settings**
   - Enable **ActiveX and Socket Clients**
   - Note the **Socket port** (defaults: 7497 paper / 7496 live; gateway uses 4001/4002)
3. Open `~/.compare_my_stocks/data/myconfig.yaml` and set the port to match:

   ```yaml
   Sources: !SourcesConf
     IBSource: !IBSourceConf
       PortIB: 7497   # whatever TWS shows
   ```

Pictures: [wiki page on TWS configuration](https://github.com/eyalk11/compare-my-stocks/wiki/Configurations#configurations-in-trader-workstation).

### 2b. Polygon

1. Sign up at <https://polygon.io/> and create an API key.
2. Edit `myconfig.yaml`:

   ```yaml
   Sources: !SourcesConf
     PolySource: !PolyConf
       Key: "YOUR_KEY_HERE"
   Input: !InputConf
     InputSource: !InputSourceType Polygon
   ```

---

## 3. First launch

Developer:

```powershell
python -m compare_my_stocks --console
```

End user (installed `.exe`):

```powershell
compare-my-stocks.exe --console
```

`--console` keeps the terminal attached so you can see startup logs. Drop it
once everything works.

On first run the app creates `~/.compare_my_stocks/`, copies defaults, and
opens the main window. If IB is configured it spawns the **ibsrv** sidecar
in the background — that's normal.

---

## 4. Import your transactions (optional but recommended)

You don't need transactions just to plot prices, but you do need them for
**P&L / portfolio** features.

### From My Stocks Portfolio (any broker)

1. Export your portfolio CSV from the [My Stocks Portfolio](https://play.google.com/store/apps/details?id=co.peeksoft.stocks) Android app.
2. Drop it in the data dir as `example_mystock.csv` (or change `SrcFile` in config).

### From Interactive Brokers (IB Flex)

1. In IB Account Management, create a **Flex Query** for trades.
2. Get your **Flex Token**.
3. Add to `myconfig.yaml`:

   ```yaml
   TransactionHandlers: !TransactionHandlersConf
     IB: !IBConf
       FlexToken: "YOUR_TOKEN"
       FlexQuery: "YOUR_QUERY_ID"
   ```

---

## 5. Make your first graph

1. In the **Symbol** list, pick one or more tickers (e.g. `AAPL`, `MSFT`).
2. In the **Type** dropdown, pick **PRICE** (or **COMPARE** to plot relative
   to a baseline like QQQ).
3. Click **Generate**.

A line plot appears. From here you can:

- Toggle **Compare with** to normalize against a benchmark.
- Set a date range with the slider.
- Define a **Group** (e.g. "Airlines") and unite by avg price/perf.
- **Save** the graph parameters — they go into `graphs.json`.

Examples and more advanced flows are in the [README](https://github.com/eyalk11/compare-my-stocks#examples)
and the [wiki](https://github.com/eyalk11/compare-my-stocks/wiki).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| App opens then nothing happens | Run with `--console` to see logs. |
| `IB connection failed` | TWS not running, or `PortIB` doesn't match the socket port shown in TWS. |
| Wrong currency | Check `Symbols.Basecur`, `ExchangeCurrency`, and `StockCurrency` in config. |
| Display looks tiny / huge | Set `Running.TryToScaleDisplay: false` in config. |
| Errors at shutdown in `--nogui` | Known, ignore — see [CLAUDE.md](https://github.com/eyalk11/compare-my-stocks/blob/master/CLAUDE.md). |

Logs live in `~/.compare_my_stocks/log.txt` and `error.log`.

---

## Install profiles

| Extra | Use it for |
|---|---|
| `[full]` | Everything (default for users) |
| `[full_no_ib]` | Everything except `ib_insync` |
| `[mini]` | Bare minimum runtime |
| `[jupyter]` | Adds embedded Jupyter / Voila |

Example:

```powershell
pip install "compare-my-stocks[mini]"
```

---

## Next steps

- **[CONFIGURATION.md](CONFIGURATION.md)** — every config option, what it does, the default.
- **[README.md](https://github.com/eyalk11/compare-my-stocks#readme)** — feature tour and screenshots.
- **[Wiki](https://github.com/eyalk11/compare-my-stocks/wiki)** — extra guides and pitfalls.

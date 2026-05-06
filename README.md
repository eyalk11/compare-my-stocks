# Compare My Stocks

> Visualize and compare the performance of stocks in your portfolio — by
> ticker, by sector, against benchmarks, and against your own realized P&L.

`compare-my-stocks` is a desktop app (PySide6/Qt + matplotlib + pandas) with
deep Interactive Brokers and Polygon integration, plus an embedded Jupyter
notebook for ad‑hoc analysis. **BYOK** (Bring Your Own Keys): you keep your
data, the app just visualizes it.

📚 **Docs:** [GitHub Pages](https://eyalk11.github.io/compare-my-stocks/) · [Quick start](docs/QUICKSTART.md) · [Configuration reference](docs/CONFIGURATION.md) · [Wiki](https://github.com/eyalk11/compare-my-stocks/wiki)

---

## Examples

**Profit per sector vs the entire portfolio**, since a chosen date:

![sectors](https://user-images.githubusercontent.com/72234965/147883101-d565a1b1-eb57-4877-9a2c-706d63b48076.png)

(You won't see your portfolio until you upload your transactions.)

**A specific airline, the airlines as a group, and Nasdaq**:

![airlines](https://user-images.githubusercontent.com/72234965/149631950-742d1a08-06f7-43ba-a1a3-fa7785f84edf.png)

ESYJY here is ~48% behind the Nasdaq since 04/01/2021 — and significantly
behind airlines as a group. That kind of cross-cut is the point of the app.

---

## Why use it

- **Cross-sectional comparison.** Group your tickers (e.g. "Airlines",
  "Cloud") and compare a group's average against any other ticker, group,
  or your portfolio.
- **Real P&L.** Pull realized + unrealized profit, automatically synced
  with IB, split-adjusted, currency-normalized.
- **No vendor lock-in.** Works offline once data is cached. Export to CSV.
  Load your own Jupyter notebook for custom analysis.
- **Free and open source.** No subscription, no telemetry.

---

## Features

✅ Working &nbsp;&nbsp; ⚪ Present but not finished &nbsp;&nbsp; ⚕️ Planned

### Market data
- ✅ Price history from **Interactive Brokers** (via the `ibsrv` sidecar)
- ✅ Price history from **Polygon**
- ✅ Crypto and ETFs
- ✅ Stocks from any exchange IB supports

### Portfolio
- ✅ Import transactions from [My Stocks Portfolio](https://play.google.com/store/apps/details?id=co.peeksoft.stocks) CSV — works with **any broker**
- ✅ Pull transactions from **IB Flex**
- ✅ Realized + unrealized P&L
- ✅ Currency normalization (set a base currency; everything converts)
- ✅ Holdings auto-adjusted for stock splits

### Graphs
- ✅ Many graph types: Total Profit, Price, Realized Profit, Compare, …
- ✅ Compare vs another ticker, vs a group, vs your portfolio
- ✅ Show % change / % diff from a chosen point, max, or min
- ✅ Pick top-N stocks or filter by value range
- ✅ Unite a group by avg price or avg performance
- ✅ Save and reload graph parameter presets (`graphs.json`)
- ⚪ Compare your actual P&L against a hypothetical "what if I'd bought the index instead" portfolio

### Jupyter integration
- ✅ Embedded notebook with the current graph's data preloaded
- ✅ Edit & reload notebook directly from the app
- ✅ One-line correlations: `mydata.act.df.corr(method='pearson')`
- ✅ Generate graphs from code:
  ```python
  gen_graph(Parameters(type=Types.PRICE | Types.COMPARE,
                       compare_with='QQQ', groups=["FANG"]))
  ```
- ⚪ Inline graphs in Jupyter

### More
- ✅ Define & edit categories / groups in the GUI
- ✅ Completely free and open source

### Planned
- ⚕️ P/E and price-to-sales overlays
- ⚕️ Bar graphs
- ⚕️ Inflation-adjusted performance
- ⚕️ Web frontend
- 🔴 *Not* planned: technical-analysis indicators

---

## Install

End users should grab the Windows installer from
[Releases](https://github.com/eyalk11/compare-my-stocks/releases).

This is actually recommended to everyone if not want to mess with Python and dependencies — the installer bundles everything.

For developers, the easiest path is the bundled PowerShell installer
**[`install/installdev.ps1`](install/installdev.ps1)** (Python 3.11) — it runs
`pip install "compare-my-stocks[full]"` and copies the bundled defaults into
`~/.compare_my_stocks/`. Pass `-currentbranch` to install from the current
checkout instead of PyPI:

```powershell
./install/installdev.ps1                  # install from PyPI
./install/installdev.ps1 -currentbranch   # install from this checkout
```


The pip-based developer install should also work on macOS and Linux, but
those platforms are untested — `installdev.ps1` itself requires PowerShell,
so on non-Windows you'll need to run its `pip install` and data-copy steps
by hand.

Full instructions, IB / Polygon configuration, and your first graph are in
**[docs/QUICKSTART.md](docs/QUICKSTART.md)**.

---

## Configuration

All behavior is controlled by `~/.compare_my_stocks/data/myconfig.yaml`.
Every option is documented in **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)**,
along with the most common tweaks (longer history, different data source,
display scaling, …).

Highly configurable.

---

## Running

```powershell
python -m compare_my_stocks               # normal launch (developer)
compare-my-stocks.exe                     # normal launch (installed)

python -m compare_my_stocks --console     # keep the console attached
python -m compare_my_stocks --debug       # DEBUG-level logging
python -m compare_my_stocks --nogui       # headless mode
python -m compare_my_stocks --config-file D:\alt.yaml
```

If something looks wrong, **always start with `--console`** to see logs.

---

## Architecture (1‑minute version)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│  gui (Qt)    │────▶│ CompareEngine│────▶│  GraphGenerator      │
│  mainwindow  │     │  orchestrator│     │  (matplotlib)        │
└──────────────┘     └──────┬───────┘     └──────────────────────┘
                            │
            ┌───────────────┼─────────────────┐
            ▼               ▼                 ▼
     ┌────────────┐  ┌──────────────┐  ┌──────────────────┐
     │ InputProc. │  │ Transactions │  │ DataGenerator    │
     │ (IB/Poly/  │  │ (IB Flex +   │  │ (price/profit/   │
     │  Cache)    │  │  MyStocks)   │  │  compare/group)  │
     └─────┬──────┘  └──────────────┘  └──────────────────┘
           │
           ▼
     ┌─────────────┐         ┌──────────────────────────┐
     │  ibsrv.exe  │ ◀────── │  Pyro5 RPC (separate     │
     │  sidecar    │         │  process; isolates IB)   │
     └─────────────┘         └──────────────────────────┘
```

More detail in `CLAUDE.md` and the wiki.

---

## Tests

```powershell
pytest src/compare_my_stocks/tests
```


---

## Contributing

Issues and PRs welcome. Pre-existing wiki:
[Things good to know when using the app](https://github.com/eyalk11/compare-my-stocks/wiki/Things-good-to-know-when-using-the-app).

If you want to dig into the code:

- `CLAUDE_REPO.md` — architecture overview and conventions (also useful for humans)
- `docs/CONFIGURATION.md` — every config field
- `src/compare_my_stocks/engine/compareengine.py` — the orchestrator
- `src/compare_my_stocks/processing/` — data transforms
- `src/compare_my_stocks/ibsrv.py` — the IB sidecar process

---

## Compatibility & remarks

- **OS:** developed and tested on Windows. Other OSes are unverified.
- **Display:** designed around 1920×1080. Auto-scales for other resolutions;
  set `Running.TryToScaleDisplay: false` if the auto-scale misfires.
- **Data location:** the app creates `~/.compare_my_stocks/` (override via
  `COMPARE_STOCK_PATH`) for logs, caches, and config.
- **Python & Pandas pin:** `pandas==1.5.3` is intentional — caches on disk are pickled
  with that version. Don't upgrade without migrating the cache.
  Will change soon. That also means Python 3.11 is required, since Pandas 1.5 is not  supported on 3.12 .

---

## Legal

1. **No warranty.** IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM,
   DAMAGES OR OTHER LIABILITY ARISING FROM USE OF THIS SOFTWARE — including
   any claim associated with usage of the Interactive Brokers API. Consult
   the relevant providers' licenses before use.
2. The software can consume CSVs exported from **My Stocks Portfolio &
   Widget** by Peeksoft.
3. This project was developed individually, in spare time, without
   compensation. The author is not affiliated with Interactive Brokers,
   Polygon, Peeksoft, or any mentioned company.
4. The author takes no responsibility for the correctness of any displayed
   graph or computed P&L.

---

## Contact

Eyal Karni · <eyalk5@gmail.com> · contributions and bug reports welcome.

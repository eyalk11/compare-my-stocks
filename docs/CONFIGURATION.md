# Configuration Reference

`compare-my-stocks` reads its configuration from a YAML file —
**`myconfig.yaml`** — at startup. This page documents every section, the
defaults, and the most useful tweaks.

> Just want to get going? See [QUICKSTART.md](QUICKSTART.md).

---

## Where the config lives

The app looks for `myconfig.yaml` in this order:

1. The path passed via `--config-file <path>` on the command line.
2. The path in the `COMPARE_STOCK_CONFIG_FILE` environment variable.
3. `~/.compare_my_stocks/data/myconfig.yaml` (or `<COMPARE_STOCK_PATH>/data/`).
4. The bundled default at `<install>/data/myconfig.yaml`.

**The directory containing the located `myconfig.yaml` becomes the data
directory** — every relative path in the config (`HistF`, `JsonFilename`,
log files, …) is resolved under that directory. Set
`COMPARE_STOCK_PATH=<some-dir>` to force a specific data dir explicitly.

The schema (auto-generated from the dataclasses in `config/newconfig.py`)
ships as `myconfig.schema.json` next to the config — most editors will
auto-validate via the YAML language-server header at the top of the file.

---

## Top-level sections

```yaml
!Config
DefaultParams:        # what to plot at startup
Earnings:             # earnings-overlay cache
File:                 # filenames for caches and persisted state
Input:                # which market-data source, how to cache
Running:              # logging, debug flags, scaling
Sources:              # IB / Polygon credentials
Symbols:              # currency / exchange normalization
TransactionHandlers:  # IB Flex + My Stocks CSV
UI:                   # figure size, layout
Voila:                # embedded notebook server
Jupyter:              # notebook config (optional)
```

Each is explained below. Defaults shown match `src/compare_my_stocks/data/myconfig.yaml`.

---

## `DefaultParams`

The graph that opens automatically at launch.

```yaml
DefaultParams: !DefaultParamsConf
  CacheUsage: !UseCache FORCEUSE   # FORCEUSE | USEIFAVAILABLE | DONT
  Ext:                             # tickers to plot at startup
    - QQQ
    - AAPL
  DefaultGroups: []                # group names to plot at startup
```

| Field | Meaning |
|---|---|
| `CacheUsage` | `FORCEUSE` skips network fetches at startup. Use `USEIFAVAILABLE` to refresh stale data. |
| `Ext` | Tickers added to the initial graph. |
| `DefaultGroups` | Stock groups (defined in `groups.json`) plotted at startup. |

---

## `Input`

Controls **which** market-data source is used and **how aggressively** the
on-disk cache is reused.

```yaml
Input: !InputConf
  InputSource: !InputSourceType IB     # IB | Polygon | Cache | InvestPy
  FullCacheUsage: !UseCache DONT
  MaxCacheTimeSpan: !!python/object/apply:datetime.timedelta [1, 0, 0]
  DefaultFromDate: 2022-01-01 00:00:00+00:00
  DownloadDataForProt: true
  IgnoreAdjust: false
  TzInfo: !!python/object/apply:datetime.timezone [...]
```

| Field | Default | Meaning |
|---|---|---|
| `InputSource` | `IB` | Market-data backend. `Cache` plays back without hitting the network. |
| `FullCacheUsage` | `DONT` | Whether to reuse a single full-history cache file. Most users leave this. |
| `MaxCacheTimeSpan` | 1 day | Cache entries older than this are refreshed. |
| `MaxFullCacheTimeSpan` | 20 days | Same, but for the consolidated full cache. |
| `DefaultFromDate` | 2022‑01‑01 | Earliest date to pull. **Lower this if you want longer history.** |
| `DownloadDataForProt` | true | Auto-download history for every ticker in your portfolio. |
| `IgnoreAdjust` | false | Skip split adjustments (rarely needed). |
| `TzInfo` | local | Timezone used when parsing IB timestamps. |
| `MinDaysForSymbol` | 7 | Drop symbols with fewer than N days of data. |
| `PricesAreAdjustedToToday` | true | Prices are normalized to today's split factors. |

---

## `Sources`

Credentials for the chosen data source. **At least one of these must be
configured** — usually the one matching `Input.InputSource`.

```yaml
Sources: !SourcesConf
  IBSource: !IBSourceConf
    HostIB: 127.0.0.1
    PortIB: 7596             # MUST match the socket port in TWS
    IBSrvPort: 9091          # Pyro5 port between app and ibsrv sidecar
    AddProcess: ibsrv.exe    # name/path of the IB sidecar binary
    MaxIBConnectionRetries: 3
    PromptOnConnectionFail: true
    DefaultExchange: SMART
    UsePythonIfNotResolve: true
    RegularAccount: null
    RegularUsername: null
  PolySource: !PolyConf
    Key: null                # Polygon API key
```

**`PortIB`** is the most common cause of "IB connection failed". Open TWS,
go to **Edit → Global Configuration → API → Settings**, and copy the
**Socket port** value here.

`AddProcess` controls whether the app spawns the `ibsrv` sidecar
automatically (`ibsrv.exe` on Windows, set to a list `["python", "ibsrv.py"]`
in dev). Set to `null` to disable autospawn.

---

## `TransactionHandlers`

Where your portfolio history comes from. The app supports IB Flex and
*My Stocks Portfolio* CSVs simultaneously.

```yaml
TransactionHandlers: !TransactionHandlersConf
  TransactionSource: !TransactionSourceType Both    # IB | MyStocks | Both
  CombineStrategy: !CombineStrategyEnum PREFERSTOCKS
  IB: !IBConf
    FlexToken: null            # paste your IB Flex token
    FlexQuery: null            # paste the IB Flex query ID
    DoQuery: true
    TryToQueryAnyway: false
    Use: !UseCache USEIFAVAILABLE
    CacheSpan: 5h
    PromptOnQueryFail: true
  MyStocks: !MyStocksConf
    SrcFile: example_mystock.csv
    PortofolioName: My Portfolio
    File: buydicnk.cache
  StockPrices: !StockPricesConf
    Use: !UseCache USEIFAVAILABLE
    File: stocksplit.cache     # split cache so holdings are split-adjusted
  MaxPercDiffIbStockWarn: 0.2  # warn when IB and CSV disagree by >20%
```

### Combine strategies

| Strategy | Behavior |
|---|---|
| `PREFERSTOCKS` | When both sources have a transaction, take the *My Stocks* version. |
| `PREFERIB` | Prefer IB. |
| `MERGE` | Best-effort merge of both lists. |

---

## `Symbols`

Currency and exchange normalization. Critical if your portfolio spans
multiple exchanges.

```yaml
Symbols: !SymbolsConf
  Basecur: USD                  # all P&L / prices reported in this currency
  DefaultCurr: [USD, EUR, GBP, ILS]
  Exchanges: [NYSE, nasdaq, xetra, London, "OTC Markets"]
  ExchangeCurrency:
    London: GBP
    Xetra: EUR
  StockCurrency: {}             # per-ticker overrides, e.g. {VOD: GBP}
  Translatedic:                 # rename tickers as they come in
    ADA-USD: cardano
    VUKE.L: VUKE
  IgnoredSymbols: []
  Crypto: !!set {}              # set of symbols treated as crypto
  CurrencyFactor:               # divide raw prices by this (e.g. ILA → ILS x 100)
    ILS: 100.0
    ILA: 100.0
  TranslateCurrency: { ILA: ILS }
```

Most users only touch `Basecur`, `IgnoredSymbols`, and occasionally
`Translatedic` (when a broker reports a ticker under a name yfinance/IB
doesn't recognize).

---

## `Running`

Logging, debugging, and behavior switches.

```yaml
Running: !RunningConf
  Debug: 1                       # 0 off, 1 default, 2 verbose
  StopExceptionInDebug: true
  VerifySaving: !VerifySave Ask  # Ask | Always | DONT
  LoadLastAtBegin: true          # restore the last-used graph at startup
  CheckReloadInterval: 3         # seconds between auto-reload checks (dev)
  LastGraphName: Last
  LogFile: log.txt
  LogErrorFile: error.log
  StartIbsrvInConsole: false
  TryToScaleDisplay: true        # auto-scale on non-1080p screens
  IsTest: false                  # set automatically by the test harness
```

| Field | When to change |
|---|---|
| `TryToScaleDisplay` | Set `false` if the UI looks broken on your monitor. |
| `LoadLastAtBegin` | Set `false` if you want a clean slate at every launch. |
| `VerifySaving` | `DONT` to skip the "save graph?" prompt. |
| `Debug` | Bump to `2` for verbose engine logs (also pass `--debug` on CLI). |

---

## `File`

Filenames the app reads/writes inside the data directory. Rarely worth
changing — but useful to know if you want to inspect cache files manually.

```yaml
File: !FileConf
  HistF: HistFile.cache               # pickled price history
  HistFBackup: HistFile.cache.back
  JsonFilename: groups.json           # user-defined groups
  GraphFN: graphs.json                # saved graph parameter presets
  SerializedFile: serialized.dat.json # GUI ↔ Jupyter handoff
  DefaultNotebook: jupyter\DefaultNotebook.ipynb
  DataFilePtr: DATA_FILE
  ExportedPort: exported.csv
  EarningStorage: earnings.dat
```

> The price-history cache (`HistFile.cache`) is pickled with **pandas 1.5.3**.
> Don't upgrade pandas without a migration — see `CLAUDE.md`.

---

## `UI`

```yaml
UI: !UIConf
  DefFigSize: !!python/tuple [6.6, 3.0]   # (width, height) in inches
  AdditionalOptions: {}
  UseQT: 1
  UseWX: 0
  UseWEB: 0
  SimpleMode: 0
  CircleSize: 360            # scatter dot size
  CircleSizePercentage: 0.05
  MinColForColumns: 20
```

`DefFigSize` is the most useful one — bump it on a 4K monitor.

---

## `Voila` / `Jupyter`

Embedded notebook server. Touch only if you use the Jupyter integration.

```yaml
Voila: !VoilaConf
  DontRunNotebook: false
  AutoResovleVoilaPython: true   # find a Python interpreter automatically
  VoilaPythonProcessPath: null   # or set explicitly
  MaxVoilaWait: 9                # seconds to wait for Voila to start

Jupyter: !JupyterConf
  MemoFolder: ".\\memory"
  Expries: 24
  TranslateSymbols: {}
```

---

## `Earnings`

Caches the earnings dates overlay (small markers on the price chart).

```yaml
Earnings: !EarningsConf
  Use: !UseCache USEIFAVAILABLE
  CacheSpan: 40 days
  File: earnings.cache
  NoEarnings: false
  MaxElements: 10
  EarningsAtStart: true
  ThreadTimeout: 8
  MaxSpanToRefershEntry: 120 days
  IgnoreSymbols: !!set {}
```

Set `NoEarnings: true` to skip earnings entirely (faster startup).

---

## API keys (RapidAPI helpers)

Two optional RapidAPI integrations:

```yaml
SeekingAlphaHeaders: !RapidKeyConf
  XRapidApiHost: 'seeking-alpha.p.rapidapi.com'
  XRapidApiKey: null

StockPricesHeaders: !RapidKeyConf
  XRapidApiHost: 'stock-prices2.p.rapidapi.com'
  XRapidApiKey: null
```

Only fill these in if you specifically want SeekingAlpha headlines or the
RapidAPI stock-prices fallback.

---

## Common tweaks at a glance

| Goal | Change |
|---|---|
| Pull longer history | `Input.DefaultFromDate: 2015-01-01 …` |
| Use Polygon instead of IB | `Input.InputSource: Polygon` + `Sources.PolySource.Key` |
| Disable IB sidecar autospawn | `Sources.IBSource.AddProcess: null` |
| Skip earnings overlay | `Earnings.NoEarnings: true` |
| Bigger plots | `UI.DefFigSize: [12.0, 6.0]` |
| Always run headless | `python -m compare_my_stocks --nogui` |
| Use a different data dir | `set COMPARE_STOCK_PATH=D:\stocks` |
| Use a one-off config | `python -m compare_my_stocks --config-file D:\alt.yaml` |

---

## Schema

The full schema is generated from
[`config/newconfig.py`](https://github.com/eyalk11/compare-my-stocks/blob/master/src/compare_my_stocks/config/newconfig.py) and
shipped as
[`myconfig.schema.json`](https://github.com/eyalk11/compare-my-stocks/blob/master/src/compare_my_stocks/data/myconfig.schema.json).
Pointing your editor at this schema gives autocomplete and inline
validation.

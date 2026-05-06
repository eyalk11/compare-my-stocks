# Compare My Stocks — Documentation

A desktop app for visualizing and comparing stock performance, portfolio
P&L, and sector groupings. Market data from **Interactive Brokers** or
**Polygon**; transactions from **IB Flex** or *My Stocks Portfolio* CSVs.

---

## Where to start

<div class="grid cards" markdown>

- :material-rocket-launch: **[Quick start](QUICKSTART.md)** \
  Install, point the app at IB or Polygon, plot your first graph in 10 minutes.

- :material-window-maximize: **[UI reference](UI.md)** \
  Field guide to every control, list, and toggle in the main window.

- :material-cog: **[Configuration reference](CONFIGURATION.md)** \
  Every field in `myconfig.yaml`, what it does, and the default value.

- :material-book-open-variant: **[Project README](https://github.com/eyalk11/compare-my-stocks#readme)** \
  Feature overview, screenshots, and the architecture diagram.

- :material-test-tube: **[Tests overview](https://github.com/eyalk11/compare-my-stocks/blob/master/TESTS.md)** \
  How the test suite is wired and how to run it.

</div>

---

## Common tasks

| I want to… | Look at |
|---|---|
| Install and run for the first time | [Quick start](QUICKSTART.md) |
| Switch from IB to Polygon | [Configuration → Sources](CONFIGURATION.md#sources) |
| Pull more history | [Configuration → Input](CONFIGURATION.md#input) |
| Import my IB transactions | [Quick start → step 4](QUICKSTART.md#4-import-your-transactions-optional-but-recommended) |
| Use a different data directory | Set `COMPARE_STOCK_PATH=…` |
| Run headless | `python -m compare_my_stocks --nogui` |

---

## Get help

- **Bugs / feature requests:** [GitHub issues](https://github.com/eyalk11/compare-my-stocks/issues)
- **Tips & pitfalls:** [project wiki](https://github.com/eyalk11/compare-my-stocks/wiki)
- **Email:** <eyalk5@gmail.com>

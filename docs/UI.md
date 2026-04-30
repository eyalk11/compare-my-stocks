# UI Reference

A field guide to every control in the **compare-my-stocks** main window. If
you've already done [Quick start](QUICKSTART.md) and just want to know what
each button does, this is the page.

> Layout: the left side is the chart; the right side is a tall control
> column with stocks at the top, graph-type/operations in the middle, and
> groups/adjustments/saved-graphs along the bottom. Everything redraws
> automatically (Auto Update is on by default).

---

## 1. Picking stocks

The top-right "**Pick Stock**" panel is where you build the list of tickers
that show up in the graph.

| Control | What it does |
|---|---|
| **Symbol combo** (`addstock`) | Type or pick a ticker. Lists every symbol the app currently knows about (see *usable symbols* below). |
| **Lookup** (`lookupsym_btn`) | Asks the data source (IB / Polygon) for matching contracts. Use this when you only know part of the company name or want the exact contract for a non-US listing. Opens the [Pick Symbol dialog](#pick-symbol-dialog). |
| **Add to >** (`addreserved`) | Add the typed/selected ticker to the **Reference** list. |
| **< Add to** (`addselected`) | Add it to the **Selected** list. |

Below that are two side-by-side lists:

- **Selected** (`orgstocks`) — the *primary* tickers the chart draws lines for.
- **Reference** (`refstocks`, also called *ext*) — extra always-on lines drawn alongside. They bypass the value-range filters (sec. 6) and don't get sorted/truncated, so they're a good place for benchmarks (QQQ, SPY, …).

Between the two lists are mover buttons:

| Button | Action |
|---|---|
| `>` (`addtoref`) | Move highlighted entries from **Selected** to **Reference**. |
| `<` (`addtosel`) | Move highlighted entries from **Reference** to **Selected**. |
| `X` (`deletebtn`) | Delete highlighted entries from whichever list has focus. |

> **Tip — *usable symbols*:** the symbol combo only lists tickers the app
> already has data for in its cache plus your portfolio holdings. To use a
> ticker the app has never seen, type it in and press **Lookup** so it gets
> resolved against IB/Polygon and added to the cache.

### Pick Symbol dialog

Opened by **Lookup**. Shows the contracts IB returned for your query, with
columns for symbol, exchange, type, currency, and description. Click a row,
hit **OK**, and that fully-qualified contract is added (its IB conId is
stashed via `resolve_hack` so subsequent runs skip the lookup step).

---

## 2. Use Groups

Above or beside the lists is the **Use Groups** checkbox (`use_groups`).
This is the single most important toggle:

- **Checked** — the chart's primary tickers come from the selected
  **Groups** (see sec. 7), not the **Selected** list. The Selected list
  becomes informational. This is how you say "show me the Pharma group" or
  "show me FANG."
- **Unchecked** — the **Selected** list drives the chart directly.

The **Reference** list is honored either way.

---

## 3. Main Graph Type

Inside "**Main Options → Main Graph Type**" — pick one. These are the
*Y-axis quantities*:

| Type | Meaning |
|---|---|
| **Price** | Close price (or adjusted close) per day. |
| **Price/Sells** | Price-to-sales ratio. |
| **Value** | Value of your *current holding* of the stock (qty × price). |
| **P/E** | Price/earnings ratio (only when earnings data is available). |
| **Total Profit** | Realized + unrealized profit on your holding. |
| **Unrealized Profit** | Mark-to-market profit on shares you still hold. |
| **Realized** | Profit booked on shares you've already sold. |
| **Theortical** | "What if I'd held the same dollar amount in *Compare With* the entire time?" — a counterfactual benchmark for your own performance. |

Profit / Value lines need transaction data (IB Flex import or My Stocks
CSV). Without it those choices are empty.

---

## 4. Operation

"**Main Options → Operation**" — how to *transform* the Y values.

| Operation | What it draws |
|---|---|
| **Absolute** | The raw value, untransformed. |
| **Percentage** | % change relative to the **Relative to** anchor (sec. 5). |
| **Diff** | Absolute difference vs. the anchor. |
| **Percentage Diff** | % change of *the stock* minus % change of the **Compare With** stock. Lets you separate "this stock went up 30%" from "the market went up 25%, this one went up 5% extra". |

**Do Comparision** (`COMPARE`) — the checkbox above. When on, the chart
divides/subtracts every line by **Compare With** (sec. 8) before applying
the operation, so the benchmark sits at 0% / 1.0 and everything else moves
relative to it.

---

## 5. Relative to

Picks the *anchor point* used by **Percentage**, **Diff**, and the relative
forms of `Theortical`:

| Choice | Anchor |
|---|---|
| **Start Time** | First date in the visible range. |
| **End Time** | Last date in the visible range. |
| **Max** | Each stock's own peak in the range. |
| **Min** | Each stock's own trough in the range. |

For example: **Percentage + Relative to Start Time** gives "% change since
the start date"; **Percentage + Relative to Max** gives "% drawdown from
peak".

---

## 6. Filtering ("Display")

Squeezes the chart down to a manageable number of lines. Useful for "top
gainers in this group" / "biggest holdings only" views.

| Control | Effect |
|---|---|
| **Displayed Num** (`max_num`) | Only show the top-N (or bottom-N, or [start, end]) stocks by the chosen criterion. |
| **Value** range (`min_crit`) | Only include stocks whose value falls in this range. |
| **Based On** radios — **Range / Max / Min** | Whether the *Value* range is tested against each stock's [min, max], its max only, or its min only. |
| **Filter zero values** (`filter_zeros`) | Drop stocks whose values are all zero (or all NaN). |

**Reference** stocks (`refstocks`) ignore these filters — they're always
drawn.

---

## 7. Groups

Groups are named bags of tickers. They live in `~/.compare_my_stocks/groups.json`.

| Control | What it does |
|---|---|
| **Category combo** (`categoryCombo`) | Pick the *category* (top-level grouping). The default install ships with `Fields`, `Sectors`, `Industry`, `Country`. Each category has its own set of groups. |
| **Groups list** (`groups`) | Tick the groups you want active. With **Use Groups** on, all stocks in the ticked groups are drawn. |
| **Edit Groups** (`edit_groupBtn`) | Open the group editor (rename groups, add/remove tickers, reorder). |
| **Sort Alphabetically** (`sortGroupsBtn`) | Re-sort the groups list. |
| **Select All/None** (`selectallnone`) | Toggle all groups in the list. Use with care — selecting "all" pulls every ticker. |
| **Limit to portfolio stocks** (`limit_to_port`) | Intersect the group expansion with your current portfolio, so a group like "Tech" only shows the tech stocks you actually own. |

**Portfolio** is a built-in pseudo-group containing every ticker in your
current portfolio (computed from imported transactions).

---

## 8. Compare With

`comparebox` — a single-ticker dropdown for the benchmark. Used when **Do
Comparison** is on (sec. 4). Typically `QQQ` or `SPY`.

You can also point it at one of the special pseudo-symbols:

- **`#USD`, `#EUR`, `#ILS`, …** — the historical exchange rate of that
  currency vs. your `Basecur` (default: USD). For the base currency itself
  this is a flat 1.0 line. Useful for "did this stock beat the dollar?"
  comparisons.

> If you pass a *group name* into Compare With and the same group is in
> your active groups list with a SUM/AVG unite (sec. 9), the comparison
> uses the group sum as the benchmark. The app will also try to fetch a
> ticker by that name as a side effect — harmless, just noisy in the log.

---

## 9. Way to unite

When **Use Groups** is on, you can collapse each group into a single line:

| Mode | Each group's line is… |
|---|---|
| **None** | Don't unite — every constituent stock is drawn separately. |
| **Sum** | Sum of constituents (per date). Equal-weighted. |
| **Average** | Mean of constituents. |
| **Max** / **Min** | Highest / lowest stock in the group, per date. |

Plus two add-on toggles that work with any unite mode:

- **Add Portfolio to graph** (`unite_ADDPROT`) — adds an extra line that's
  the *value-weighted* sum of your current portfolio.
- **Add Total to Graph** (`unite_ADDTOTAL`) — adds a line that's the sum of
  every visible ticker.

---

## 10. Date range

| Control | What it does |
|---|---|
| **Start / End date pickers** | Set the visible date range. |
| **Date range slider** (`daterangepicker`) | Drag either handle to scrub the range. |
| **Until Now** (`til_todayBtn`) | Snap the end date to today. |

The chart's X axis matches this range exactly. Refreshing **does not** pull
data outside it (use **Refresh Stocks** sec. 13 for that).

---

## 11. Currency adjustments

In "**Groups And Adjustments → Adjustments**":

| Control | What it does |
|---|---|
| **Adjust Currency** (`adjust_currency`) | When on, every value is converted to the currency in **Current Currency**. When off, everything is in `Basecur` (default USD). |
| **Current Currency** (`home_currency_combo`) | The display currency. ILS, EUR, etc. |

Behind the scenes the app uses live FX rates from your data source (with a
historical-rate fallback for older dates). The conversion is applied to
prices, value, and profit columns.

---

## 12. Saved graphs

Bottom right, "**Saved Graphs**":

| Control | Action |
|---|---|
| **Saved graphs list** (`graphList`) | Click a name to load that saved configuration. |
| **Save** (`save_graph_btn`) | Save the current settings under a name (you'll be prompted). |
| **Load** (`load_graph_btn`) | Re-load the highlighted entry. |
| **Clear all** (`clearBtn`) | Wipe the saved graphs list (asks first). |

Saved graphs live in `~/.compare_my_stocks/graphs.json`. They include every
setting on this page: types, groups, dates, filters, compare_with, etc.
The app remembers the last graph you used and reloads it on startup.

---

## 13. Action buttons

Across the bottom strip:

| Button | What it does |
|---|---|
| **Refresh Stocks** (`refresh_stock`) | Re-query the data source for the visible date range. Use after adding new tickers or extending the date range. |
| **Update Graph** (`update_btn`) | Force a redraw without re-querying. Useful for visual glitches. |
| **Auto Update** (`auto_update`) | When on (default), the chart redraws on every setting change. Turning it off is rarely needed. |
| **Min Refersh** (`minrefresh`) | When on, refresh only fetches the *missing* days, not the entire range. Faster but skips correcting any silent gaps. |
| **Visible to selected** (`vis_to_selectedBtn`) | Copy whatever is currently visible (after filters / Show-Hide) into the **Selected** list. Only works with **Use Groups** off. |
| **Show / Hide** (`showhide`) | Toggle the per-stock show/hide column on the chart. |
| **Show Transactions** (`checkBox_showtrans`) | Overlay buy / sell markers on the chart. |
| **Start Hidden** (`start_hidden`) | New graphs start with all lines hidden — click each one to reveal it. Handy for very large groups. |
| **Use refernce stocks** (`usereferncestock`) | Master switch for the **Reference** list. When off, those lines are excluded entirely. |
| **Open Status** (`open_statusbtn`) | Pop a window listing every ticker with its data-fetch status (good / bad / partial / cached date). |
| **Export Portofolio** (`exportport`) | Write a CSV of your current portfolio (IB transactions + manual entries combined). |

---

## 14. Display modes

Top-right radio strip:

| Mode | What you get |
|---|---|
| **Minimal Mode** | Compact layout — the bottom controls collapse, leaving more chart area. |
| **Jupyter Mode** | Replaces (or adds to) the chart area with the embedded notebook. |
| **No Jupyter** | Hides the notebook even if it would have loaded. |
| **Full Mode** | Everything visible. Default. |

---

## 15. Embedded notebook

Inside the **Your Notebook** panel (visible in **Jupyter Mode** /
**Full Mode**):

| Control | What it does |
|---|---|
| **Reload** (`reload_notebook`) | Re-execute the embedded notebook (`defaultnotebook.ipynb`). Use after modifying it. |
| **Open In Jupyter** (`debug_btn`) | Launch the notebook in a real Jupyter window. Nicer for editing. |
| **Switch Notebook** (`pushButton`) | Swap to a different `.ipynb` file. |

The notebook gets the current `CompareEngine` injected as a Python kernel
variable, so you can write your own analysis using whatever the GUI is
already showing.

---

## 16. Limitations to know

A few things the UI accepts that don't quite work the way you'd expect.
None will crash; they just silently do something less useful than they
look like.

- **A group name in the Reference list** is *not* expanded. Putting `FANG`
  there treats it as a literal ticker — you'll get an unrelated stock or a
  fetch error. To use a group as a reference line, put it in the **Groups**
  list with **Sum** unite instead.
- **A group name in `addstock`/Selected** (with **Use Groups** off) — same
  thing, treated as a literal ticker.
- **`Compare With` set to a group** works *only* if the same group is in
  your active groups list with SUM/AVG unite. The app will additionally try
  to fetch a stock by that name; it'll fail and log a warning.
- **Refreshing the date range** doesn't auto-pull missing transactions
  outside the range. If you extend the date range backwards, hit
  **Refresh Stocks** to pull the older data.
- **Filter rows** (sec. 6) ignore Reference lines, so adding many of them
  defeats the "top-N" effect.

---

## See also

- [Quick start](QUICKSTART.md) — install and first-graph walkthrough.
- [Configuration reference](CONFIGURATION.md) — every field in `myconfig.yaml`.
- [GitHub README](https://github.com/eyalk11/compare-my-stocks#readme) — screenshots and architecture.

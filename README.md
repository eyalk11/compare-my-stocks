# stocks-visualizer-jupyter

== General ==
Visualize Stocks in your portfolio using matplotlib and jupyter. 

The idea is to provide commands for generating useful portfolio graphs inline in jupyter. 
For instance, to compare the performance of the FANG stocks in your portfolioto a stock of your choice (i.e. QQQ) in a single command, that you could execute when you want.


![image](https://user-images.githubusercontent.com/72234965/134824596-3660e4e0-9d73-4dac-82c8-60a21730fced.png)


It also opens a UI to generate this command easily. 

The input data I currently have is a MyStockProtfolio CSV (any csv that describes buys/sells), and will add later  Interactive brokers account's positions. 
The additional input data is account in Interactive Brokers as it works with IB gateway to obtain price history for all relevant stocks. 

**Having said that, it is in preliminary condition and not guaranteed to work, currently.**

![image](https://user-images.githubusercontent.com/72234965/134824685-dba476e4-6a84-47b4-a37d-db7247324414.png)


== Running Instructions ===

1. Copy example_config and change accordingly.

Notice that you should provide a CSV in MyStocksProtoflio format: (at least) 
Id	Symbol	Name  Portfolio	 Price	Quantity	Cost Per Share	 Date	TimeOfDay	Type

for every transaction (Type is Buy/Sell). 

2. If you want to use the provided cache, increase the MAXCACHETIMESPAN siginificantly. Otherwise, provide IB data and run client portal gateway.
3. Run the provided sample.ipynb in jupyter (using TK with getpositionsgraph.py is supported too, but doesn't include a dialog).

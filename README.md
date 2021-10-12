# Compare My Stocks

## General 
Visualize the performance of stocks in your portfolio or that  you are interested in.
You can use a variaty of comparision options. 

For instance: 

* Divide the stocks into sectors, and compare the performance of different sector
* See a chart of stocks divided to groups/sectors - 
    * chart of average price change of  FANG vs interesting stock in  China) 
    * chart of profit of each section 
* Compare your profit with a theoritical situation in which you have bought the index!




![comparestockscreen](https://user-images.githubusercontent.com/72234965/137033857-71283f52-59d7-4356-8f5c-8d43037ebf15.png)

The input data I currently have is a MyStockProtfolio CSV (any csv that describes buys/sells), and will add later  Interactive brokers account's positions. 
The additional input data is account in Interactive Brokers as it works with IB gateway to obtain price history for all relevant stocks. 

**Having said that, it is in preliminary condition and not guaranteed to work, currently.**

## Additional Features 

* Get transactions from My Stocks Protofolio 
* Maximal control over comparisions 
* Use jupyter to quickly change paramters of the graph! 
 
* Find corelations between sectors  (planned)
* Suited for your protoflio (no manual comparision)
* Interacts with IB to get transaction (planned)
* Exporting dataframes to  jupyter (planned)



## Running Instructions

 1. Copy exampleconfig.py to config.py
 2. Change according to instructions there.

    Notice that you should provide a CSV in MyStocksProtoflio format for every transaction (Type is Buy/Sell):


 3. Use Inverstpy from my branch
 4. Run mainwindow.py

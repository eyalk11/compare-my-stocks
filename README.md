# Compare My Stocks

## General 
Visualize the performance of stocks in your portfolio or that  you are interested in.
There is maximal control over charts, and a variaty of comparision options. 

For instance: 

You can divide the stocks into sectors, and compare the performance of different sector! 

* chart of average price change of  FANG vs interesting stock in  China) 
* chart of profit of each section 

You can compare your profit at any time to a theoretical situation in which you have bought the index(the exact same time you have made a purchase)!

![comparestockscreen](https://user-images.githubusercontent.com/72234965/137033857-71283f52-59d7-4356-8f5c-8d43037ebf15.png)

The input data I currently have is a MyStockProtfolio CSV (any csv that describes buys/sells), and will add later Interactive brokers account's positions. 
The stocks historical prices are obtained from investpy (originally https://github.com/alvarobartt/investpy) .


## Additional Features 

* Compare performance with any stock
* Unite stocks into groups
* Compare with entire protofolio 
* Get price history from Investpy (uses inversting.com) 
* Get transactions from My Stocks Protofolio (by simple file export) - https://play.google.com/store/apps/details?id=co.peeksoft.stocks 
* Combined protofolio from any broker/investments
* Use jupyter to quickly change paramters of the graph! 
* Completely free and open source. 

## Planned
* Introducing advanced features like P/E and price to sells . 
* Find corelations between sectors  
* Interacts with IB to get transaction 
* Exporting dataframes to jupyter (should be easy)
* Crypto support(should be easy)


## Running Instructions

** Preliminary version, many features are not working yet ** 

 1. Copy exampleconfig.py to config.py
 2. Change according to instructions there.

    Notice that you should provide a CSV in MyStocksProtoflio format for every transaction (Type is Buy/Sell):


 3. Depends on inverstpy. Please use https://github.com/eyalk11/investpy for it to work.
 4. Run mainwindow.py

## Contact Me

Feel free to contact me at eyalk5@gmail.com 

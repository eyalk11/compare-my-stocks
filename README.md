
# Compare My Stocks

## General 
Visualize the performance of stocks in your portfolio or that  you are interested in.
There is maximal control over charts, and a variaty of comparision options. 

You can divide the stocks into sectors, and compare the performance of different sector! 

For instance: 

* **Chart of profit of sectors in your portfolio and of the entire portfolio relative to a certain point in time.** 

![image](https://user-images.githubusercontent.com/72234965/147883101-d565a1b1-eb57-4877-9a2c-706d63b48076.png)

(You won't see your portfolio unless you will upload your transactions)  

* **Chart of specific airlines and the airlines as a group compared with nasdaq:**
 
![image](https://user-images.githubusercontent.com/72234965/149631950-742d1a08-06f7-43ba-a1a3-fa7785f84edf.png)


(The difference in the change percentage-wise since 04/01/2021 between ESYJY and the nasdaq is ~48% at this point at time, signficantly lower than the airlines as a group. This is example of an advanced usage.)

##  Features 
⚕️	Planned
✅ Working 
⚪ Present but not working yet

 
### **Stocks from all over the world**
 
&nbsp;&nbsp;&nbsp;&nbsp; ✅ Get price history from Interactive Brokers 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Crypto support 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ ETF support 

### **Connect with your portfolio**

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Export your transactions from [My Stocks Protofolio](https://play.google.com/store/apps/details?id=co.peeksoft.stocks) 

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (Doesn't matter which broker you work with)

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Pull transactions data directly from Interactive Brokers TWS. 

### **Smart Calculations**

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Adjust Prices and profit relative to a currency. 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Adjust holdings based on stock splits (using stockprices API). 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Combine IB transaction data into MyStocksPortfolio (by exporting csv). 

### **Maximum control over graphs**

 &nbsp;&nbsp;&nbsp;&nbsp; ✅ Compare performance of group of stocks vs other stock vs your portfolio! 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Many graph types ( Total Profit, Price, Realized Profit, etc...) 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Display percentage change / percentage diff , from certain time / maximum / minimum 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Pick only top stocks for graphs / limit by value range

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Groups of stock can be united by avg price/performance 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Save and load graphs with all parameters instantly! 

&nbsp;&nbsp;&nbsp;&nbsp; ⚪ Compare your profit to a theoretical situation in which you have bought the index!

&nbsp;&nbsp;&nbsp;&nbsp; &nbsp;&nbsp;&nbsp;&nbsp; (the exact same time you have made a purchase)


### **Close Integration With Jupyter**

&nbsp;&nbsp;&nbsp;&nbsp; ✅  Display your jupyter notebook with graph! 

&nbsp;&nbsp;&nbsp;&nbsp; &nbsp;&nbsp;&nbsp;&nbsp;  i.e. find corelations in your graph (a single line of code. presented by default)
```
mydata.act.df.corr(method='pearson')
```

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Mainipulate data easily in runtime and display graph externally


&nbsp;&nbsp;&nbsp;&nbsp; ⚪ Use Jupyter to display graphs inline (if you want) 
```
gen_graph(Parameters(type=Types.PRICE | Types.COMPARE,compare_with='QQQ',groups=["FANG"],  starthidden=0))
```

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Edit/reload notebook directly





### More


✅ Edit categories and groups (using a GUI interface)! 

&nbsp;&nbsp;&nbsp;&nbsp;  i.e. Airlines stocks, Growth stocks (Can be compared as a group)


✅ **Completely free and open source!** 


## Planned Features

⚪ Introducing advanced features like P/E and price to sells.

⚪ Get price history from Interactive Brokers 

⚕️	Bar graphs (hmmmm, not critical.. ) 

⚕️ Adjusted performance based on inflation. 





⚕️ All this in a web interface!


🔴 Not planned - all these technical analysis nonsense..



## Installation Instructions


### For Developers 

 1. pip install --no-binary  :all: git+https://github.com/eyalk11/compare-my-stocks.git (or pip install -r requirments.txt)
 2. Install [Qt6](https://www.qt.io/download) If you want to edit ui file in designer

* Depends on json_editor - https://github.com/eyalk11/json-editor 

### For Users

 1. Extract compare-my-stocks.zip from the releases

### For both 
Remark: Really recommended steps, but will work basically without it

 3. Look at myconfig.py and set it as you wish .

    Notice that it is recommended to provide a CSV in MyStocksProtoflio format for every transaction (Type is Buy/Sell):
 4. Follow the steps for configuring IB 

### Remarks 
* **Not fully tested, and prerelease. Some features may not work correctly.** 
* *This program is quite complex and requires non-trivial configuration to work with it properly. I haven't got the time to make it completely user-friendly, so I'd say it requires some developer's mentality as things stand now.*


## Configuring Interactive Brokers
 
 1. Run Trader Workstation and sign in (could be readonly).
   
 2.  API -> Settings -> Enable ActiveX And Socket Clients
 3.  Make sure PortIB matches the port in there.
 (   [Here with pictures](https://github.com/eyalk11/compare-my-stocks/wiki/Configurations#configurations-in-trader-workstation) )


 
 ## Running Instructions
 1. Run Trader Workstation and sign in (could be readonly). It could be also done after running the app. 
 2. (For developers) python -m compare_my_stocks 
 2. (For users) run compare-my-stocks.exe


## Legal Words

I would like to add that: 

1. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. That is also true for the any claim associated with usage of Interactive Brokers Api by this code. 

Please consult the corresponding site's license before using this software, and use it accordingly. 

2. The sofware can use CSVs obtained from using My Stocks Portfolio & Widget by Peeksoft.   

3. This project was developed individually in my free time and without any compensation. I am an in no way affiliated with the mentioned companies. 

4. I of course take no responsibilty on the correctness of the displayed graphs/data. 

5. Investpy is not supported currently. So you have to have an account in interactive brokers to be able to work properly with it.

## Final words
* This is being developed in QT with matplotlib amd pandas. I tried to use advanced features of pandas and numpy for fast calculation(sometimes).

* I belive this software provides many useful features that are usually paid for. This despite developing this in a short period, on my spare time. I would very much apperiate community contribution. And welcome you to contribute, send bugs and discuss (will open gitter when appropriate). 

* The controls should be self explantory... Try it. 
 
* Feel free to contact me at eyalk5@gmail.com.



# Compare My Stocks

## General 
Visualize the performance of the stocks in your portfolio or those you're keenly observing. Gain utmost control over your charts, backed by a broad spectrum of comparison options. For instance, you're empowered to juxtapose an entire sector against a single stock. Moreover, you can efficiently view both realized and unrealized profit charts, which are automatically synced with Interactive Brokers (if you have an account).


Essentially, this app adopts a **BYOK** approach(**B**ring **Y**our **O**wn **K**eys). While it primarily uses Interactive Brokers for sourcing market data, it also boasts a fresh integration with Polygon.

Moreover, you can personalize your experience further by bringing your own notebook, allowing you to deploy your favorite algorithms for stock analysis.

### Examples 
You can divide the stocks into sectors, and compare the performance of different sector! 

For instance: 

* **Graph of profit of sectors in your portfolio and of the entire portfolio relative to a certain point in time.** 

![image](https://user-images.githubusercontent.com/72234965/147883101-d565a1b1-eb57-4877-9a2c-706d63b48076.png)

(You won't see your portfolio unless you will upload your transactions)  

* **Graph of specific airlines and the airlines as a group compared with nasdaq:**
 
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

 1. `pip install compare-my-stocks[full]` 
 2. Consider updating ibflex (from git) as the app in pypi is quite old ( `pip install git+https://github.com/csingley/ibflex.git`)
 3. Better to copy  `site-packages\compare_my_stocks\data` to `~/.compare_my_stocks` 

### For Users

 1. Use setup
 2. If something goes wrong, you can view console with `compare_my_stocks.exe --console`.  Recommended. There is also log file. 

### For both 

 3. Inspect  `data/myconfig.yaml` and set it as you wish ( usually it is in `~/.compare_my_stocks/data` ). It has a lot of options. 

    It is recommended to provide a CSV in *MyStocksProtoflio* format for every transaction
    (The app comes with an example) 
 
 4. Choose your favorite input source (IB or Polygon ): 

#### Configuring Interactive Brokers
[detailed instructions with pictures](https://github.com/eyalk11/compare-my-stocks/wiki/Configurations#configurations-in-trader-workstation)


 
 1. Run Trader Workstation and sign in (could be readonly).
   
 2.  API -> Settings -> Enable ActiveX And Socket Clients
 3.  Make sure PortIB matches the port in there.

#### Configuring Polygon 
 1. Click "Create API Key" on  https://polygon.io/  
 2. Choose a plan 
 3. Copy the key to config and select polygon input source: 
```
!Config
  ...
  Sources: !SourcesConf
    ...
    PolySource: !PolyConf
      Key: "YOURKEY"
  ... 
  Input: !InputConf
  ...
    INPUTSOURCE: !InputSourceType Polygon
```

 
 ## Running Instructions
 1. Run Trader Workstation and sign in (could be readonly). It could be also done after running the app. 
 2. (For developers) `python -m compare_my_stocks` 
 2. (For users) run `compare-my-stocks.exe` (shortcut)

## Reocommanded reading

To avoid some pitholes , it is recommended to check out this list: 

[Things good to know when using the app](https://github.com/eyalk11/compare-my-stocks/wiki/Things-good-to-know-when-using-the-app)


## Remarks 

* This app works best on 1920x1080, but is adaptive to othe resoultions. 
If it looks very  bad , set `TRY_TO_SCALE_DISPLAY` in config to False.

* Not tested on OS other than windows. 

* If face problems run with `--console` to see what is happening 

* If you are developer and don't like the console, run with `--noconsole`.

* This app / setup creates the folder `~/.compare_my_stocks` and use it to store logs and data. It has algorithm for resolving the different paths. It also read env variable `COMPARE_STOCK_PATH` .


## Legal Words

I would like to add that: 

1. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. That is also true for the any claim associated with usage of Interactive Brokers Api by this code. 

Please consult the corresponding site's license before using this software, and use it accordingly. 

2. The sofware can use CSVs obtained from using My Stocks Portfolio & Widget by Peeksoft.   

3. This project was developed individually in my free time and without any compensation. I am an in no way affiliated with the mentioned companies. 

4. I of course take no responsibilty on the correctness of the displayed graphs/data. 

## Final words

*  Not fully tested, and prerelease. Still has surprisingly low number of bugs :)
   
* This is being developed in QT with matplotlib amd pandas. I tried to use advanced features of pandas and numpy for fast calculation(sometimes).

* I belive this software provides many useful features that are usually paid for. This despite developing this in a short period, on my spare time. I would very much apperiate community contribution. And welcome you to contribute, send bugs and discuss (will open gitter when appropriate). 

* The controls should be self explantory... Try it. Some things requres some developer mentality.. 
 
* Feel free to contact me at eyalk5@gmail.com.


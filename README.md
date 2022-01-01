
# Compare My Stocks

## General 
Visualize the performance of stocks in your portfolio or that  you are interested in.
There is maximal control over charts, and a variaty of comparision options. 

You can divide the stocks into sectors, and compare the performance of different sector! 

For instance: 

* **Chart of profit of stocks in your portfolio belonging to each sector.** 

* **Chart of specifc airlines and the Nasdaq vs the airlines as a group:**
 
![image](https://user-images.githubusercontent.com/72234965/147842609-bf1323af-a4dd-48e1-ae71-c7d95109b990.png)

* **Chart of different  FANG stocks vs Nasdaq vs Biontech:** 
 
![image](https://user-images.githubusercontent.com/72234965/137415199-b4d6d463-5ef0-4cc9-930c-58b086a94f5b.png)



##  Features 
⚕️	Planned
✅ Working 
⚪ Present but not working yet

 
### **Stocks from all over the world!**
 
&nbsp;&nbsp;&nbsp;&nbsp; ✅ Get price history from Investpy (uses inversting.com)  

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Crypto support 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ ETF support 

### **Connect with your portfolio!**

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Export your transactions from [My Stocks Protofolio](https://play.google.com/store/apps/details?id=co.peeksoft.stocks) 

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (Doesn't matter which broker you work with. You can also adapt other transaction tables..)

&nbsp;&nbsp;&nbsp;&nbsp; ⚕️ Pull transactions data directly from Interactive Brokers TWS. 

### **Maximum control over graphs!**

 &nbsp;&nbsp;&nbsp;&nbsp; ✅ Compare performance of group of stocks vs other stock vs your portfolio! 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Many graph types ( Total Profit, Price, Realized Profit, etc...) 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Display percentage change / percentage diff , from certain time / maximum / minimum 

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Pick only top stocks for graphs / limit by value range

&nbsp;&nbsp;&nbsp;&nbsp; ✅ Groups of stock can be united by avg price/performance 

&nbsp;&nbsp;&nbsp;&nbsp; ⚪ Compare your profit to a theoretical situation in which you have bought the index!

&nbsp;&nbsp;&nbsp;&nbsp; &nbsp;&nbsp;&nbsp;&nbsp; (the exact same time you have made a purchase)

### Misc features 

✅ Adjusted performance relative to a currency of your choice! 

✅ Save and load graphs with all parameters instantly! 

✅ Edit categories and groups (using a GUI interface)! 

&nbsp;&nbsp;&nbsp;&nbsp;  i.e. Airlines stocks, Growth stocks (Can be compared as a group)

✅ Use Jupyter to display graphs inline (if you want) 
```
gen_graph(type=Types.PRICE | Types.COMPARE,compare_with='QQQ',groups=["FANG"],  starthidden=0)
```

✅ **Completely free and open source!** 

## Planned Features

⚕️	Bar graphs 

⚕️ Adjusted performance based on  inflation. 

⚪ Introducing advanced features like P/E and price to sells.

⚕️ Find corelations between sectors  

⚕️ Close Integration  with jupyter (like export and import graph data) 

⚕️ All this in a web interface!

🔴 Not planned - all these technical analysis nonsense..



## Running Instructions

Remark: **Not fully tested, and prerelease. Some features may not work correctly.** 

 1. Install Qt 
 2. Install using setup.py
 3. Look at config/config.py and follow instructions there (will work without it).

    Notice that you should provide a CSV in MyStocksProtoflio format for every transaction (Type is Buy/Sell):
 
 4. Run main.py


* Depends on inverstpy and json_editor. Needed https://github.com/eyalk11/investpy  https://github.com/eyalk11/json-editor 

## Legal Words

I would like to add that: 

1. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. That is also true for the any claim associated with inderict usage of Investing.com( using investpy), as well as Interactive Brokers Api by this code. 

Please consult the corresponding sites' license before using this software, and use it accordingly. See also the disclaimer https://github.com/eyalk11/investpy.

2. The sofware might use csvs obtained from using  My Stocks Portfolio & Widget by peeksoft.   

3. This project was developed individually in my free time and without any compensation. I am an in no way affiliated with the mentioned companies. 

4. I of course take no responsibilty on the correctness of the displayed graphs/data. 

## Final words
* This is being developed in QT with matplotlib amd pandas. I tried to use advanced features of pandas and numpy for fast calculation(sometimes).



* I belive this software is already usable and provide many useful features that are usually paid for. This despite developing this in a short period, on my spare time. I would very much apperiate community contribution. And welcome you to contribute, send bugs and discuss (will open gitter when appropriate). 

* If you have an idea about how it will be best integrated with active stock research using Jupyter Lab or something else, let me know. 

* The controls should be self explantory... Try it. 
 
* Feel free to contact me at eyalk5@gmail.com.


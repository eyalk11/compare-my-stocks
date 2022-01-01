# Compare My Stocks

## General 
Visualize the performance of stocks in your portfolio or that  you are interested in.
There is maximal control over charts, and a variaty of comparision options. 

For instance: 

You can divide the stocks into sectors, and compare the performance of different sector! 

* chart of average price change of  FANG vs interesting stock in  China) 
* chart of profit of each section 

You can even compare your profit at any time to a theoretical situation in which you have bought the index(the exact same time you have made a purchase)!

![image](https://user-images.githubusercontent.com/72234965/137415199-b4d6d463-5ef0-4cc9-930c-58b086a94f5b.png)

This is being developed in QT with matplotlib. 

I used advance features of python, numpy and pandas for fast calcuation. 

The input data I currently have is a MyStockProtfolio CSV (any csv that describes buys/sells), and will add later Interactive brokers account's positions. 
The stocks historical prices are obtained from investpy (originally https://github.com/alvarobartt/investpy) .


## Additional Features 

* Compare performance with any stock
* Selct stocks and graphs by groups
* Unite groups by avg price/performance and see as one line.
* Compare performance of stocks with entire protofolio 


* Get price history from Investpy (uses inversting.com) 
* Get transactions from My Stocks Protofolio (by simple file export) - https://play.google.com/store/apps/details?id=co.peeksoft.stocks 
(Independent  from any broker/investments product)
* Use jupyter to quickly change paramters of the graph! i.e. 
```
gen_graph(type=Types.PRICE | Types.COMPARE,compare_with='QQQ',groups=["FANG"],  starthidden=0)
```
* Completely free and open source. 

## Planned
* Bar graphs
* Adjusted performance based on cash transactions / inflation. 
* Introducing advanced features like P/E and price to sells, with all possible comparisions.  
* Find corelations between sectors  
* Interacts with Interactive Brokers to get transaction 
* Exporting dataframes to jupyter (should be easy)
* Crypto support(should be easy)


## Running Instructions

** Preliminary version, many features are not working yet ** 

 1. Copy exampleconfig.py to config.py
 2. Change according to instructions there.

    Notice that you should provide a CSV in MyStocksProtoflio format for every transaction (Type is Buy/Sell):


 3. Depends on inverstpy. Please use https://github.com/eyalk11/investpy for it to work.
 4. Run main.py

## Legal Words

I would like to add that: 
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. That is also true for the any claim associated with inderict usage of Investing.com( using investpy), as well as Interactive Brokers Api by this code. 

I am in way affiliated with them. Please consult the corresponding sites' license before usage, and use it appropriately. See also the disclaimer https://github.com/eyalk11/investpy

## Final words

I wanted this product to be used inline in jupyter notebook. This is not possible with the way it is currently QT (having full features). 

I am not sure about the right level of exposure to code. 

Should I allow for customized, code-based operations between stocks? I am not a fun of GUI, and it is a lot of work. 
Include notebook inside QT? What kind of statisitics to incorporate? 


Feel free to contact me at eyalk5@gmail.com.


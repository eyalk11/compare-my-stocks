from transactions.transactioninterface import TransactionHandlerInterface



class TrasnasctionHandler(TransactionHandlerInterface):
    def __init__(self,manager):
        self._manager  =manager
        #self.symbol_info=defaultdict(dict)
        self._buydic = {}
        self._buysymbols = set()

    @property
    def buysymbols(self) -> set:
        return self._buysymbols

    @property
    def buydic(self) -> dict:
        return self._buydic

    def get_portfolio_stocks(self):  # TODO:: to fix
        return self._buysymbols #[config.TRANSLATEDIC.get(s,s) for s in  self._buysymbols] #get_options_from_groups(self.Groups)

    def update_sym_property(self, symbol, value, prop='currency', updateanyway=True):
        current=  self._manager.symbol_info.get(symbol)
        if current:

            current=current.get(prop)
        if not current:
            self._manager.symbol_info[symbol][prop] = value
        elif current!=value:
            print(f'diff {prop} for {symbol} {current} {value}')
            if updateanyway:
                self._manager.symbol_info[symbol][prop] = value





    def process_transactions(self):
        if self.try_to_use_cache():
            print('using buydict cache ')
            return
        self._buydic = {}
        self._buysymbols = set()

        self.populate_buydic()


        self.save_cache()


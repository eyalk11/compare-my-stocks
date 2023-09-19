import dataclasses
import datetime
import traceback
from functools import reduce, partial
from io import StringIO
from typing import Dict, List, Union, Set
import dacite
from dataclasses import  field

from pydantic import ConfigDict

from common.common import UseCache, InputSourceType, CombineStrategyEnum, VerifySave, TransactionSourceType
import pytz
import logging
from common.loghandler import init_log, dont_print, init_log_default
import os
import sys
from typing import Optional
from common.common import log_conv
from common.paramaware import paramaware
from common.simpleexceptioncontext import SimpleExceptionContext

RESOLVE_FILES = ['LogFile', 'LogErrorFile', 'IBLogFile', 'IBLogErrorFile']
FILE_LIST_TO_RES = ["HistF", "HistFBackup", "JsonFilename", "SerializedFile", "RevenueFile", "IncomeFile",
                            "CommonStock", "GraphFN", "DefaultNotebook", 'DataFilePtr', 'ExportedPort','IbSrvReady','FullData']

#from pydantic.dataclasses import dataclass as pyddataclass
#confdict=ConfigDict(arbitrary_types_allowed=True)
#dataclass=partial(pyddataclass,config=confdict)
from dataclasses import dataclass

@paramaware
@dataclass
class StockPricesConf:
    Use: Union[UseCache, int] = UseCache.USEIFAVALIABLE
    CacheSpan: datetime.timedelta = datetime.timedelta(days=40)
    File: str = r'stocksplit.cache'
    IgnoreSymbols: Set[str] = field(default_factory=set)


@paramaware
@dataclass
class IBConf:
    File: str = r'ibtrans.cache'
    CacheSpan: datetime.timedelta = datetime.timedelta(hours=5)
    Use: Union[UseCache, int] = UseCache.USEIFAVALIABLE
    TryToQueryAnyway: bool = False
    DoQuery: bool = True
    FlexToken: Optional[str] = None
    FlexQuery: Optional[str] = None
    QueryIfOlderThan: datetime.timedelta = datetime.timedelta(days=3)
@paramaware 
@dataclass 
class PolyConf: 
    Key: Optional[str] = None 

@dataclass
class MyStocksConf:
    File: str = r'buydicnk.cache'
    SrcFile: str = "example_mystock.csv"
    PortofolioName: str = "My Portfolio"
    Use: Union[UseCache, int] = UseCache.USEIFAVALIABLE


@paramaware
@dataclass()
class TransactionHandlersConf:
    '''
    Configurations for transactions handlers.

    Args:
        TrackStockList (List): stocks to track(add logging messages) . It always prints the operations but also the list of times.


    '''
    JustFromTheEndOfMyStock : bool = False
    TransactionSource:  TransactionSourceType = TransactionSourceType.Both
    TrackStockDict : Dict[str,Set[datetime.datetime]] = field(default_factory=dict)

    ReadjustJustIB : bool = False
    DontAdjustSplitsMyStock : bool = False
    DontReadjust : list = field(default_factory=list)
    SaveCaches: bool = True
    StockPrices: StockPricesConf = field(default_factory=StockPricesConf)
    IB: IBConf = field(default_factory=IBConf)
    MyStocks: MyStocksConf = field(default_factory=MyStocksConf)
    IgnoreConf: Dict = field(default_factory=lambda: {})
    CombineStrategy: CombineStrategyEnum = CombineStrategyEnum.PREFERSTOCKS
    IncludeNormalizedOnSave: bool = True
    MaxPercDiffIbStockWarn: float = 0.2 #ignored currently
    FixBuySellDiffDays: int = 3
    BothSymbols: List = field(default_factory=lambda: [])
    SupressCommon : bool = False
    CombineDateDiff : int = 20
    CombineAmountPerc : int  = 10


@dataclass
class RapidKeyConf:
    XRapidApiHost: Optional[str] = None
    XRapidApiKey: Optional[str] = None

@paramaware
@dataclass
class IBSourceConf:
    HostIB: str = '127.0.0.1'
    PortIB: int = 7596
    IBSrvPort: int = 9091
    AddProcess: Optional[Union[str, List]] = 'ibsrv.exe'
    MaxIBConnectionRetries: int = 3
    RegularAccount: Optional[str] = None
    RegularUsername: Optional[str] =None
    UsePythonIfNotResolve: bool = True
@paramaware
@dataclass
class UIConf:
    AdditionalOptions: dict = field(default_factory=lambda: {})

    UseWX: int = 0
    UseWEB: int = 0
    UseQT: int = 1
    MinColForColumns: int = 20
    DefFigSize: tuple = (13.2 * 0.5, 6 * 0.5)
    SimpleMode: int = 0
    CircleSizePercentage: float = 0.05
    CircleSize :int = 5*72

@paramaware
@dataclass
class TestingConf:
    AddProcess: Optional[Union[str, List]] = field(default_factory=lambda: ["python", "ibsrv.py"])


@paramaware
@dataclass
class RunningConf:
    IsTest: bool = False
    StopExceptionInDebug: bool = True
    VerifySaving: VerifySave = VerifySave.Ask
    Debug: int = 1
    StartIbsrvInConsole : bool =False
    CheckReloadInterval: Optional[int] = 30 #reload modules
    LastGraphName: str = "Last"
    LoadLastAtBegin: bool = True
    IBLogFile: Optional[str] = "iblog.txt"
    LogFile: Optional[str] = "log.txt"
    LogErrorFile: Optional[str] = "error.log"
    UseAlterantiveLocation: Optional[bool] = None #to load data from original location
    TwsProcessName : Optional[str] = "tws.exe"
    SleepForIbsrvToStart: int = 5
    IBLogErrorFile: Optional[str] = "ibsrv_error.log"
    DisplayConsole : bool =False
    Title: str = "Compare My Stocks"
    TryToScaleDisplay : bool = True
@paramaware
@dataclass
class EarningsConf:
    SkipEarnings: int = 1
    TryStorageForEarnings: int = 1
@paramaware
@dataclass
class DefaultParamsConf:
    CacheUsage: UseCache = UseCache.FORCEUSE
    Ext: list = field(default_factory=list)
    DefaultGroups: list = field(default_factory=list)


@paramaware
@dataclass
class SymbolsConf:
    ValidExchanges: list = field(default_factory=list)
    TranslateExchanges: dict = field(default_factory=dict)
    ExchangeCurrency: dict = field(default_factory=dict)
    StockCurrency: dict = field(default_factory=dict)
    IgnoredSymbols: list = field(default_factory=list)
    Translatedic: dict = field(default_factory=dict)
    Crypto: set = field(default_factory=set)
    Exchanges: list = field(default_factory=list)
    DefaultCurr: list = field(default_factory=list) #currency list
    Basecur: str = "USD"
    ReplaceSymInInput: dict = field(default_factory=dict)
    TranslateCurrency: dict = field(default_factory=dict)
    CurrencyFactor: dict = field(default_factory=dict)



@paramaware
@dataclass
class FileConf:
    HistF: str = r'HistFile.cache'
    HistFBackup: str = HistF + '.back'
    DefaultNotebook: str = r'jupyter\DefaultNotebook.ipynb'
    JsonFilename: str = r'groups.json'
    SerializedFile: str = r'serialized.dat'
    EarningStorage: str = 'earnings.dat'
    RevenueFile: str = 'NOEARNINGS'
    IncomeFile: str = 'NOEARNINGS'
    CommonStock: str = 'NOEARNINGS'
    DataFilePtr: str = 'DATA_FILE'
    GraphFN: str = 'graphs.json'
    ExportedPort: str = "exported.csv"
    IbSrvReady: str = "ibsrv_ready.txt"
    FullData: str = "fullinpdata.bin"

@paramaware
@dataclass
class InputConf:
    SaveData:bool =True 
    PricesAreAdjustedToToday:bool = True
    AdjustUnrelProfitToReflectSplits: bool = True
    MaxCacheTimeSpan: datetime.timedelta = datetime.timedelta(days=20)
    MaxFullCacheTimeSpan: datetime.timedelta = datetime.timedelta(days=1)
    FullCacheUsage: UseCache = UseCache.FORCEUSE
    AlwaysStoreFullCache: bool = False
    InputSource: InputSourceType = InputSourceType.IB
    IgnoreAdjust: int = 1 #DONT_ADJUST_FOR_CURRENT
    DownloadDataForProt: bool = True
    DefaultFromDate: datetime.datetime = datetime.datetime(2020, 1, 1, tzinfo=pytz.UTC)
    TzInfo: datetime.timezone =None # = datetime.timezone(datetime.timedelta(hours=-3),'GMT3') must provide
    MaxRelevantCurrencyTime : datetime.timedelta = datetime.timedelta(minutes=60)
    MaxRelevantCurrencyTimeHeur: datetime.timedelta = datetime.timedelta(days=5)

@paramaware
@dataclass
class VoilaConf:
    DontRunNotebook: bool = False
    VoilaPythonProcessPath: Optional[str] = None
    AutoResovleVoilaPython: bool = True
    MaxVoilaWait: int = 9

@paramaware
@dataclass
class JupyterConf:
    MemoFolder : str = '.\\memory'
    RapidYFinanaceKey: str = ''
    RapidYFinanaceHost: str = "yfinance-stock-market-data.p.rapidapi.com"
    Expries : int = 24

@paramaware
@dataclass
class SourcesConf:
    IBSource: IBSourceConf = field(default_factory=IBSourceConf)
    PolySource: PolyConf = field(default_factory=PolyConf)


@paramaware
@dataclass
class Config:

    Testing: TestingConf = field(default_factory=TestingConf)
    Running: RunningConf = field(default_factory=RunningConf)
    Earnings: EarningsConf = field(default_factory=EarningsConf)
    DefaultParams: DefaultParamsConf = field(default_factory=DefaultParamsConf)
    Symbols: SymbolsConf = field(default_factory=SymbolsConf)
    File: FileConf = field(default_factory=FileConf)
    Input: InputConf = field(default_factory=InputConf)
    Voila: VoilaConf = field(default_factory=VoilaConf)
    UI: UIConf = field(default_factory=UIConf)
    Sources: SourcesConf = field(default_factory=SourcesConf)
    TransactionHandlers: TransactionHandlersConf = field(default_factory=TransactionHandlersConf)
    StockPricesHeaders: RapidKeyConf = field(default_factory=RapidKeyConf)
    SeekingAlphaHeaders: RapidKeyConf = field(default_factory=RapidKeyConf)
    Jupyter: JupyterConf = field(default_factory=JupyterConf)


CONFIGFILENAME = 'myconfig.yaml'

MYPROJ = 'compare_my_stocks'
PROJPATHENV = 'COMPARE_STOCK_PATH'

MYPATH = os.path.dirname(__file__)

PROJDIR = os.path.join(os.path.expanduser("~"), "." + MYPROJ)


def print_if_ok(*args):
    if dont_print():
        return

    if 'SILENT' in __builtins__ and __builtins__['SILENT'] == False\
            or any('pytest' in x for x in sys.argv):
        logging.info(*args)





def resolvefile(filename,use_alternative=False):
    if not 'python' in sys.executable:
        t = os.path.dirname(sys.executable)
        datapath = os.path.join(t, 'data')
    else:
        datapath = os.path.realpath((os.path.join(MYPATH, '..', 'data')))
    env = os.environ.get(PROJPATHENV)
    paths =(env if env else []) +  [PROJDIR, "/etc/" + MYPROJ]  if not use_alternative else [] + [os.curdir, datapath]
    try:
        if filename == '':
            return False, None
        if os.path.isabs(filename):
            return os.path.exists(filename), os.path.realpath(filename)

        for loc in paths + [datapath]:
            fil = os.path.join(loc, filename)
            if os.path.exists(fil):
                return True, os.path.abspath(fil)

        return False, os.path.realpath(os.path.join(PROJDIR, filename)  if not use_alternative else os.path.join(datapath,filename)) # default location
    except:
        return False, None


# c=Config()
# c=c
# from pyhocon import ConfigParser
# ConfigParser.resolve_substitutions(partially_resolving_config, accept_unresolved=True)

class ConfigLoader():
    logging_initialized = False
    config: Config = None
    @classmethod
    def generate_config(cls):
        #never should be called. 
        cls.main()
        yaml= cls.get_yaml()
        c=Config()
        c.Input.TZINFO=None
        st=StringIO()
        yaml.dump(c, st)
        st.seek(0)
        c.Symbols=cls.config.Symbols
        with open(r'config.yaml', 'wt') as fil:
             for k in st:
                 if "_changed_keys" in k:
                     continue
                 fil.write(k)

    @classmethod
    def resolve_it(cls, obj, f,use_alternative=None):
        res, fil = resolvefile(getattr(obj, f),use_alternative=use_alternative)

        if fil == None:
            print_if_ok(f'Invalid value {f}')
            return

        if res == False:
            print_if_ok(f'Failed resolving {f}. Using: {fil}')
        else:
            print_if_ok(f'{f} resolved to {fil}')

        setattr(obj, f, fil)

    @classmethod
    def main(cls,config_file=None, use_alternative=None) -> Config:


        if cls.config is not None and not use_alternative and config_file is not None:
            return cls.config

        if not os.path.exists(PROJDIR):
            print_if_ok("""project directory doesn't exists... Creating...
            Consider copying your config files there """)
            os.makedirs(PROJDIR)

        # yaml.dump(Config(),open(r'C:\Users\ekarni\compare-my-stocks\src\compare_my_stocks\config\myconfig.yaml','wt'))
        res, config_file = resolvefile(CONFIGFILENAME,use_alternative)
        if not res:
            logging.error('No config file, aborting')
            sys.exit(-1)

        noexcep=False
        with SimpleExceptionContext(f"Failed loading config file {config_file}. aborting",always_throw=True):
            cls.config = cls.load_config(config_file)
            noexcep = True
        if not noexcep:
            sys.exit(-1)

        if use_alternative is not None:
            cls.config.Running.UseAlterantiveLocation=use_alternative
        else:
            use_alternative = cls.config.Running.UseAlterantiveLocation

        if not 'SILENT' in __builtins__ and not  any('pytest' in x for x in sys.argv):
            logging.getLogger().setLevel(logging.CRITICAL) #it is first time and not run from main => probably jupyter

        for x in RESOLVE_FILES:
            cls.resolve_it(cls.config.Running, x,use_alternative)
        if not cls.logging_initialized:
            try:
                init_log_default(cls.config)
                cls.logging_initialized=True
            except:
                logging.error("initialize logging failed!")


        print_if_ok(log_conv("Using Config File: ", config_file))



        for f in FILE_LIST_TO_RES:
            cls.resolve_it(cls.config.File,f,use_alternative)

        keys = [(c,k) for k in cls.config.__dataclass_fields__ if hasattr(c:=getattr(cls.config,k),'_changed_keys')]
        add_to_set = lambda x,y: set([f'{y}.{z}' for z in x])
        remained_keys = list(reduce(lambda x,y: x.union(y), [ add_to_set( set(c.__dataclass_fields__.keys()) - c._changed_keys,k) for c,k in keys] ))
        vals=   [ getattr(getattr(cls.config,(arr:=x.split('.'))[0]),arr[1]) for x in remained_keys]# gross

        #set(cls.config.__dataclass_fields__.keys()) - cls.config._changed_keys
        if len(remained_keys)>0:
            yy='\n'.join([': '.join( [x,str(y)]) for x,y in  zip( remained_keys,vals)])
            logging.warn(f"The following keys weren't specified in config so were set to default:\n {yy}")

        return cls.config

    @classmethod
    def load_config(cls,config_file):
        yaml= cls.get_yaml()

        from common.simpleexceptioncontext import simple_exception_handling
        #make the following a method with decorator

        @simple_exception_handling(err_description="excpetion in loading config",always_throw=True)
        def load_config_int():
            return yaml.load(open(config_file))

        conf= load_config_int()
        cls.validate_conf(conf)
        return conf


    @staticmethod
    def get_yaml():
        from ruamel.yaml import YAML
        yaml = YAML(typ='unsafe')
        import common.common
        from common.common import TransactionSourceType

        yaml.register_class(common.common.UseCache)
        yaml.register_class(common.common.CombineStrategyEnum)
        yaml.register_class(common.common.InputSourceType)
        yaml.register_class(TransactionSourceType)
        # yaml.register_class(datetime.timedelta)
        # yaml.register_class(datetime.timezone)
        yaml.register_class(common.common.VerifySave)
        yaml.register_class(Config)
        yaml.register_class(IBConf)
        yaml.register_class(PolyConf)
        yaml.register_class(TransactionHandlersConf)
        yaml.register_class(StockPricesConf)
        yaml.register_class(MyStocksConf)
        yaml.register_class(RapidKeyConf)
        yaml.register_class(UIConf)
        yaml.register_class(SourcesConf)
        yaml.register_class(IBSourceConf)
        yaml.register_class(FileConf)
        yaml.register_class(JupyterConf)
        # register all classes defined here ends with Conf
        yaml.register_class(VoilaConf)
        yaml.register_class(EarningsConf)
        yaml.register_class(RunningConf)
        yaml.register_class(DefaultParamsConf)
        yaml.register_class(SymbolsConf)
        yaml.register_class(InputConf)
        yaml.register_class(TestingConf)
        return yaml


    @classmethod
    def validate_conf(cls,config):

        try:
            tmp = dataclasses.asdict(config)

            # tmp["FlexQuery"]='aaa' #to be string
            # tmp["FlexToken"]='bbb'
            tmp["TransactionHandlers"]["IB"]["FlexToken"] = str(tmp["TransactionHandlers"]["IB"]["FlexToken"])
            tmp["TransactionHandlers"]["IB"]["FlexQuery"] = str(tmp["TransactionHandlers"]["IB"]["FlexQuery"])
            dacite.from_dict(data_class=Config, data=tmp)
        except Exception as e:
            logging.error(f"Validating conf failed {e}")
            raise e

# import dataclasses
# with open('config2.toml', 'w') as f:
#    toml.dump(c, f)

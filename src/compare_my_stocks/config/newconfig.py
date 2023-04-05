import dataclasses
import datetime
import traceback
from functools import reduce
from io import StringIO
from typing import Dict, List, Union, Set

import dacite
from dataclasses import dataclass, field

from common.common import UseCache, InputSourceType, CombineStrategy, VerifySave
import pytz
import logging
from common.loghandler import init_log
import os
import sys
from typing import Optional
from common.common import log_conv
from common.paramaware import paramaware
FILE_LIST_TO_RES = ["HIST_F", "HIST_F_BACKUP", "JSONFILENAME", "SERIALIZEDFILE", "REVENUEFILE", "INCOMEFILE",
                            "COMMONSTOCK", "GRAPHFN", "DEFAULTNOTEBOOK", 'DATAFILEPTR', 'EXPORTEDPORT']

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


@dataclass
class MyStocksConf:
    File: str = r'buydicnk.cache'
    SrcFile: str = "example_mystock.csv"
    PortofolioName: str = "My Portfolio"
    Use: Union[UseCache, int] = UseCache.USEIFAVALIABLE


@paramaware
@dataclass()
class TransactionHandlersConf:
    StockPrices: StockPricesConf = field(default_factory=StockPricesConf)
    IB: IBConf = field(default_factory=IBConf)
    MyStocks: MyStocksConf = field(default_factory=MyStocksConf)
    IGNORECONF: Dict = field(default_factory=lambda: {})
    COMBINESTRATEGY: CombineStrategy = CombineStrategy.PREFERSTOCKS
    NORMALIZE_ON_TRANSACTIONSAVE: int = 0
    MAXPERCDIFFIBSTOCKWARN: float = 0.2 #ignored currently
    FIXBUYSELLDIFFDAYS: int = 3
    BOTHSYMBOLS: List = field(default_factory=lambda: [])
    SUPRESS_COMMON : bool = False
    COMBINEDATEDIFF : int = 20
    COMBINEAMOUNTPERC : int  = 10


# TRANSACTION_HANDLERS = {
#     "StockPrices": StockPrices(
#         Use=UseCache.USEIFAVALIABLE,
#         CacheSpan=datetime.timedelta(days=40),
#         File=r'stocksplit.cache',
#         IgnoreSymbols=set([]),
#     ),
#     "IB": IB(
#         File=r'ibtrans.cache',
#         CacheSpan=datetime.timedelta(hours=5),
#         Use=UseCache.USEIFAVALIABLE,
#         TryToQueryAnyway=False,
#         DoQuery=True,
#         FlexToken='YOURTOKEN',
#         FlexQuery='QUERYNU',
#     ),
#     "MyStocks": MyStocks(
#         File=r'buydicnk.cache',
#         SrcFile="example_mystock.csv",
#         PortofolioName="My Portfolio",
#         Use=UseCache.USEIFAVALIABLE,
#     ),
# }
@dataclass
class RapidKeyConf:
    X_RapidAPI_Host: Optional[str] = None
    X_RapidAPI_Key: Optional[str] = None

@paramaware
@dataclass
class IBConnectionConf:
    HOSTIB: str = '127.0.0.1'
    PORTIB: int = 7596
    IBSRVPORT: int = 9091
    ADDPROCESS: Optional[Union[str, List]] = 'ibsrv.exe'
    MAXIBCONNECTIONRETRIES: int = 3
    REGULAR_ACCOUNT: Optional[str] = None
    REGULAR_USERNAME: Optional[str] =None
@paramaware
@dataclass
class UIConf:
    ADDITIONALOPTIONS: dict = field(default_factory=lambda: {})

    USEWX: int = 0
    USEWEB: int = 0
    USEQT: int = 1
    MINCOLFORCOLUMS: int = 20
    DEF_FIG_SIZE: tuple = (13.2 * 0.5, 6 * 0.5)
    SIMPLEMODE: int = 0


@paramaware
@dataclass
class RunningConf:
    STOP_EXCEPTION_IN_DEBUG: bool = True
    VERIFY_SAVING: VerifySave = VerifySave.Ask
    DEBUG: int = 1
    CHECKRELOADINTERVAL: Optional[int] = 30 #reload modules
    LASTGRAPHNAME: str = "Last"
    LOADLASTATBEGIN: bool = True
    LOGFILE: Optional[str] = "log.txt"
    LOGERRORFILE: Optional[str] = "error.log"

@paramaware
@dataclass
class EarningsConf:
    SKIP_EARNINGS: int = 1
    TRYSTORAGEFOREARNINGS: int = 1
@paramaware
@dataclass
class DefaultParamsConf:
    CACHEUSAGE: UseCache = UseCache.FORCEUSE
    EXT: list = field(default_factory=list)
    DefaultGroups: list = field(default_factory=list)


@paramaware
@dataclass
class SymbolsConf:
    VALIDEXCHANGES: list = field(default_factory=list)
    TRANSLATE_EXCHANGES: dict = field(default_factory=dict)
    EXCHANGE_CURRENCY: dict = field(default_factory=dict)
    STOCK_CURRENCY: dict = field(default_factory=dict)
    IGNORED_SYMBOLS: list = field(default_factory=list)
    TRANSLATEDIC: dict = field(default_factory=dict)
    CRYPTO: set = field(default_factory=set)
    EXCHANGES: list = field(default_factory=list)
    DEFAULTCURR: list = field(default_factory=list) #currency list
    BASECUR: str = "USD"



@paramaware
@dataclass
class FileConf:
    HIST_F: str = r'hist_file.cache'
    HIST_F_BACKUP: str = HIST_F + '.back'
    DEFAULTNOTEBOOK: str = r'jupyter\defaultnotebook.ipynb'
    JSONFILENAME: str = r'groups.json'
    SERIALIZEDFILE: str = r'serialized.dat'
    EARNINGSTORAGE: str = 'earnings.dat'
    REVENUEFILE: str = 'NOEARNINGS'
    INCOMEFILE: str = 'NOEARNINGS'
    COMMONSTOCK: str = 'NOEARNINGS'
    DATAFILEPTR: str = 'DATA_FILE'
    GRAPHFN: str = 'graphs.json'
    EXPORTEDPORT: str = "exported.csv"

@paramaware
@dataclass
class InputConf:
    MAXCACHETIMESPAN: datetime.timedelta = datetime.timedelta(days=1)
    INPUTSOURCE: InputSourceType = InputSourceType.IB
    IGNORE_ADJUST: int = 1 #DONT_ADJUST_FOR_CURRENT
    DOWNLOADDATAFORPROT: bool = True
    DEFAULTFROMDATE: datetime.datetime = datetime.datetime(2020, 1, 1, tzinfo=pytz.UTC)
    TZINFO: datetime.timezone =None # = datetime.timezone(datetime.timedelta(hours=-3),'GMT3') must provide

@paramaware
@dataclass
class VoilaConf:
    DONT_RUN_NOTEBOOK: bool = False
    VOILA_PYTHON_PROCESS_PATH: Optional[str] = None
    AUTO_RESOVLE_VOILA_PYTHON: bool = True
    MAX_VOILA_WAIT: int = 7

@paramaware
@dataclass
class Config:

    Running: RunningConf = field(default_factory=RunningConf)
    Earnings: EarningsConf = field(default_factory=EarningsConf)
    DefaultParams: DefaultParamsConf = field(default_factory=DefaultParamsConf)
    Symbols: SymbolsConf = field(default_factory=SymbolsConf)
    File: FileConf = field(default_factory=FileConf)
    Input: InputConf = field(default_factory=InputConf)
    Voila: VoilaConf = field(default_factory=VoilaConf)
    UI: UIConf = field(default_factory=UIConf)
    IBConnection: IBConnectionConf = field(default_factory=IBConnectionConf)
    TransactionHandlers: TransactionHandlersConf = field(default_factory=TransactionHandlersConf)
    StockPricesHeaders: RapidKeyConf = field(default_factory=RapidKeyConf)
    SEEKINGALPHAHeaders: RapidKeyConf = field(default_factory=RapidKeyConf)

CONFIGFILENAME = 'myconfig.yaml'

MYPROJ = 'compare_my_stocks'
PROJPATHENV = 'COMPARE_STOCK_PATH'

MYPATH = os.path.dirname(__file__)

PROJDIR = os.path.join(os.path.expanduser("~"), "." + MYPROJ)


def print_if_ok(*args):
    if 'SILENT' in __builtins__ and __builtins__['SILENT'] == False:
        logging.info(*args)





def resolvefile(filename):
    if not 'python' in sys.executable:
        t = os.path.dirname(sys.executable)
        datapath = os.path.join(t, 'data')
    else:
        datapath = os.path.realpath((os.path.join(MYPATH, '..', 'data')))
    env = os.environ.get(PROJPATHENV)
    paths = [PROJDIR, "/etc/" + MYPROJ] + (env if env else []) + [os.curdir, datapath]
    try:
        if filename == '':
            return False, None
        if os.path.isabs(filename):
            return os.path.exists(filename), filename

        for loc in paths + [datapath]:
            fil = os.path.join(loc, filename)
            if os.path.exists(fil):
                return True, os.path.abspath(fil)

        return False, os.path.join(PROJDIR, filename)  # default location
    except:
        return False, None


# c=Config()
# c=c
# from pyhocon import ConfigParser
# ConfigParser.resolve_substitutions(partially_resolving_config, accept_unresolved=True)

# yaml.dump(c,open(r'C:\Users\ekarni\compare-my-stocks\src\compare_my_stocks\config\config.yaml','wt'))
class ConfigLoader():
    config: Config = None
    @classmethod
    def generate_config(cls):
        cls.main()
        yaml= cls.get_yaml()
        c=Config()
        c.Input.TZINFO=None
        st=StringIO()
        yaml.dump(c, st)
        st.seek(0)
        c.Symbols=cls.config.Symbols
        with open(r'C:\Users\ekarni\compare-my-stocks\src\compare_my_stocks\config\config.yaml', 'wt') as fil:
             for k in st:
                 if "_changed_keys" in k:
                     continue
                 fil.write(k)

    @classmethod
    def resolve_it(cls, obj, f):
        res, fil = resolvefile(getattr(obj, f))

        if fil == None:
            print_if_ok(f'Invalid value {f}')
            return

        if res == False:
            print_if_ok(f'Failed resolving {f}. Using: {fil}')
        else:
            print_if_ok(f'{f} resolved to {fil}')

        setattr(obj, f, fil)

    @classmethod
    def main(cls) -> Config:


        if cls.config is not None:
            return cls.config

        if not os.path.exists(PROJDIR):
            print_if_ok("""project directory doesn't exists... Creating...
            Consider copying your config files there """)
            os.makedirs(PROJDIR)

        # yaml.dump(Config(),open(r'C:\Users\ekarni\compare-my-stocks\src\compare_my_stocks\config\myconfig.yaml','wt'))
        res, config_file = resolvefile(CONFIGFILENAME)
        if not res:
            logging.error('No config file, aborting')
            sys.exit(-1)

        try:
            cls.config = cls.load_config(config_file)
        except:
            logging.error("Failed loading config file. aborting")
            sys.exit(-1)



        for x in ['LOGFILE', 'LOGERRORFILE']:
            cls.resolve_it(cls.config.Running, x)

        try:
            log=init_log(logfile=cls.config.Running.LOGFILE, logerrorfile=cls.config.Running.LOGERRORFILE,debug=cls.config.Running.DEBUG)
        except:

            logging.error("initialize logging failed!")

        print_if_ok(log_conv("Using Config File: ", config_file))



        for f in FILE_LIST_TO_RES:
            cls.resolve_it(cls.config.File,f)

        keys = [(c,k) for k in cls.config.__dataclass_fields__ if hasattr(c:=getattr(cls.config,k),'_changed_keys')]
        add_to_set = lambda x,y: set([f'{y}.{z}' for z in x])
        remained_keys = reduce(lambda x,y: x.union(y), [ add_to_set( set(c.__dataclass_fields__.keys()) - c._changed_keys,k) for c,k in keys] )

        #set(cls.config.__dataclass_fields__.keys()) - cls.config._changed_keys
        if len(remained_keys)>0:
            yy='\n'.join(remained_keys)
            log.warn(f"The following keys weren't specified in config so were set to default:\n {yy}")

        return cls.config

    @classmethod
    def load_config(cls,config_file):
        yaml= cls.get_yaml()

        from common.common import simple_exception_handling
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
        yaml.register_class(common.common.CombineStrategy)
        yaml.register_class(common.common.InputSourceType)
        yaml.register_class(TransactionSourceType)
        # yaml.register_class(datetime.timedelta)
        # yaml.register_class(datetime.timezone)
        yaml.register_class(common.common.VerifySave)
        yaml.register_class(Config)
        yaml.register_class(IBConf)
        yaml.register_class(TransactionHandlersConf)
        yaml.register_class(StockPricesConf)
        yaml.register_class(MyStocksConf)
        yaml.register_class(RapidKeyConf)
        yaml.register_class(UIConf)
        yaml.register_class(IBConnectionConf)
        yaml.register_class(FileConf)
        # register all classes defined here ends with Conf
        yaml.register_class(VoilaConf)
        yaml.register_class(EarningsConf)
        yaml.register_class(RunningConf)
        yaml.register_class(DefaultParamsConf)
        yaml.register_class(SymbolsConf)
        yaml.register_class(InputConf)
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

# dataconf.dump(r'C:\Users\ekarni\compare-my-stocks\src\compare_my_stocks\data\myconfig.yaml',c,'yaml')
# import dataclasses
# with open('config2.toml', 'w') as f:
#    toml.dump(c, f)

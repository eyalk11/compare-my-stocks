import dataclasses
import datetime
import traceback
from typing import Dict, List, Union, Set

import dacite
import dataconf
import toml
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


@dataclass
class StockPricesConf:
    Use: Union[UseCache, int] = UseCache.USEIFAVALIABLE
    CacheSpan: datetime.timedelta = datetime.timedelta(days=40)
    File: str = r'stocksplit.cache'
    IgnoreSymbols: Set[str] = field(default_factory=set)


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


@dataclass()
class TransactionHandlersConf:
    StockPrices: StockPricesConf = field(default_factory=StockPricesConf)
    IB: IBConf = field(default_factory=IBConf)
    MyStocks: MyStocksConf = field(default_factory=MyStocksConf)


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
    X_RapidAPI_Host: str
    X_RapidAPI_Key: Optional[str]

@paramaware
@dataclass
class Config:
    TZINFO: datetime.timezone  # = datetime.timezone(datetime.timedelta(hours=-3),'GMT3') must provide
    HOSTIB: str = '127.0.0.1'
    PORTIB: int = 7596
    IBSRVPORT: int = 9091
    ADDPROCESS: str = 'ibsrv.exe'
    LOADLASTATBEGIN: bool = True
    ADDITIONALOPTIONS: dict = field(default_factory=lambda: {})
    LASTGRAPHNAME: str = "Last"
    IGNORE_ADJUST: int = 1
    SKIP_EARNINGS: int = 1
    TRYSTORAGEFOREARNINGS: int = 1
    DATAFILEPTR: str = 'DATA_FILE'
    USEWX: int = 0
    USEWEB: int = 0
    USEQT: int = 1
    SIMPLEMODE: int = 0
    DEFAULTCURR: list = field(default_factory=list)

    MAXCACHETIMESPAN: datetime.timedelta = datetime.timedelta(days=1)
    HIST_F: str = r'hist_file.cache'
    HIST_F_BACKUP: str = HIST_F + '.back'
    DEFAULTNOTEBOOK: str = r'jupyter\defaultnotebook.ipynb'
    PORT: int = 4001
    EXT: list = field(default_factory=list)
    DEF_FIG_SIZE: tuple = (13.2 * 0.5, 6 * 0.5)
    EXCHANGES: list = field(default_factory=list)
    VALIDEXCHANGES: list = field(default_factory=list)
    TRANSLATE_EXCHANGES: dict = field(default_factory=dict)
    DEFAULTFROMDATE: datetime.datetime = datetime.datetime(2020, 1, 1, tzinfo=pytz.UTC)
    EXCHANGE_CURRENCY: dict = field(default_factory=dict)
    STOCK_CURRENCY: dict = field(default_factory=dict)
    INPUTSOURCE: InputSourceType = InputSourceType.IB
    MINCOLFORCOLUMS: int = 20
    MAXCOLS: int = 30
    MINCHECKREQ: int = 10
    MINIMALPRECREQ: float = 0.2
    CACHEUSAGE: UseCache = UseCache.FORCEUSE
    DOWNLOADDATAFORPROT: bool = True
    JSONFILENAME: str = r'groups.json'
    SERIALIZEDFILE: str = r'serialized.dat'
    EARNINGSTORAGE: str = 'earnings.dat'
    TRANSLATEDIC: dict = field(default_factory=dict)
    CRYPTO: set = field(default_factory=set)
    DEBUG: int = 1
    GRAPHFN: str = 'graphs.json'
    BASECUR: str = "USD"
    REVENUEFILE: str = 'NOEARNINGS'
    INCOMEFILE: str = 'NOEARNINGS'
    COMMONSTOCK: str = 'NOEARNINGS'
    IGNORED_SYMBOLS: list = field(default_factory=list)
    EXPORTEDPORT: str = "exported.csv"
    BOTHSYMBOLS: List = field(default_factory=lambda: [])
    MAXPERCDIFFIBSTOCKWARN: float = 0.2
    FIXBUYSELLDIFFDAYS: int = 3
    NORMALIZE_ON_TRANSACTIONSAVE: int = 0
    DONT_RUN_NOTEBOOK: bool = False
    STOP_EXCEPTION_IN_DEBUG: bool = True
    VERIFY_SAVING: VerifySave = VerifySave.Ask
    CHECKRELOADINTERVAL: int = 30
    COMBINESTRATEGY: CombineStrategy = CombineStrategy.PREFERSTOCKS
    IGNORECONF: Dict = field(default_factory=lambda: {})
    LOGFILE: Optional[str] = "log.txt"
    LOGERRORFILE: Optional[str] = "error.log"
    VOILA_PYTHON_PROCESS_PATH: Optional[str] = None
    AUTO_RESOVLE_VOILA_PYTHON: bool = True
    TransactionHandlers: TransactionHandlersConf = field(default_factory=TransactionHandlersConf)
    StockPricesHeaders: RapidKeyConf = field(default_factory=RapidKeyConf)
    SEEKINGALPHAHeaders: RapidKeyConf = field(default_factory=RapidKeyConf)
    MAX_VOILA_WAIT: int = 7
    SUPRESS_COMMON : bool = False

CONFIGFILENAME = 'myconfig.yaml'

MYPROJ = 'compare_my_stocks'
PROJPATHENV = 'COMPARE_STOCK_PATH'

MYPATH = os.path.dirname(__file__)

PROJDIR = os.path.join(os.path.expanduser("~"), "." + MYPROJ)


def print_if_ok(*args):
    if 'SILENT' in __builtins__ and __builtins__['SILENT'] == False:
        logging.info(*args)


if not os.path.exists(PROJDIR):
    print_if_ok("""project directory doesn't exists... Creating...
    Consider copying your config files there """)
    os.makedirs(PROJDIR)


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
    def resolve_it(cls, f):
        res, fil = resolvefile(getattr(cls.config, f))

        if fil == None:
            print_if_ok(f'Invalid value {f}')
            return

        if res == False:
            print_if_ok(f'Failed resolving {f}. Using: {fil}')
        else:
            print_if_ok(f'{f} resolved to {fil}')

        setattr(cls.config, f, fil)

    @classmethod
    def load_config(cls) -> Config:
        if cls.config is not None:
            return cls.config
        # yaml.dump(Config(),open(r'C:\Users\ekarni\compare-my-stocks\src\compare_my_stocks\config\myconfig.yaml','wt'))
        config_file = cls.load_yaml()

        cls.validate_conf()

        for x in ['LOGFILE', 'LOGERRORFILE']:
            cls.resolve_it(x)

        try:
            init_log(logfile=cls.config.LOGFILE, logerrorfile=cls.config.LOGERRORFILE)
        except:
            logging.error("initialize logging failed!")

        print_if_ok(log_conv("Using Config File: ", config_file))


        FILE_LIST_TO_RES = ["HIST_F", "HIST_F_BACKUP", "JSONFILENAME", "SERIALIZEDFILE", "REVENUEFILE", "INCOMEFILE",
                            "COMMONSTOCK", "GRAPHFN", "DEFAULTNOTEBOOK", 'DATAFILEPTR', 'EXPORTEDPORT']
        for f in FILE_LIST_TO_RES:
            cls.resolve_it(f)

        remained_keys = set(cls.config.__dataclass_fields__.keys()) - cls.config._changed_keys
        logging.warn(f"The following keys weren't specified in config so were set to default {','.join(remained_keys)}")

        return cls.config

    @classmethod
    def load_yaml(cls):
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

        res, config_file = resolvefile(CONFIGFILENAME)
        if not res:
            logging.error('No config file, aborting')
            sys.exit(-1)
        from common.common import simple_exception_handling
        cls.config = simple_exception_handling(err_description="excpetion in loading config")(
            lambda: yaml.load(open(config_file)))()


        if cls.config is None:
            sys.exit(-1)



        return config_file

    @classmethod
    def validate_conf(cls):

        try:
            tmp = dataclasses.asdict(cls.config)

            # tmp["FlexQuery"]='aaa' #to be string
            # tmp["FlexToken"]='bbb'
            tmp["TransactionHandlers"]["IB"]["FlexToken"] = str(tmp["TransactionHandlers"]["IB"]["FlexToken"])
            tmp["TransactionHandlers"]["IB"]["FlexQuery"] = str(tmp["TransactionHandlers"]["IB"]["FlexQuery"])
            dacite.from_dict(data_class=Config, data=tmp)
        except Exception as e:
            logging.error(f"Validating conf failed {e}")
            sys.exit(-1)

# dataconf.dump(r'C:\Users\ekarni\compare-my-stocks\src\compare_my_stocks\data\myconfig.yaml',c,'yaml')
# import dataclasses
# with open('config2.toml', 'w') as f:
#    toml.dump(c, f)

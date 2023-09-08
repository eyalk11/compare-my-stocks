#Not really part of main program

import logging
import math
import os
from compare_my_stocks.common.common import Serialized
logging.getLogger().setLevel(logging.CRITICAL)
from config import config
import pickle
import numpy

from collections import defaultdict
import numpy,pandas
import os
from numerize import numerize



def query_symbol(x):
       raise NotImplemented()

def unite_if_needed(x,data,query_func=query_symbol):
    if x in data.Groups:
        dd={z: query_func(z) for z in data.Groups[x]}

        df=pandas.DataFrame.from_dict(dd)
        df=convert_to_dec(convert_to_dec(df))
        df=df.astype(float)
        df=df.mean(axis=1,skipna = True)
        df=df.apply(lambda x: numerize.numerize(x) if not math.isnan(x) else x)
        return df.to_dict()
    else:
        return query_func(x)



def load_data() -> Serialized:
    if os.path.exists(config.File.DATAFILEPTR):
        filename =open(config.File.DATAFILEPTR,'rt').read()
        if os.path.exists(filename):
            data: Serialized = pickle.load(open(filename, 'rb'))
            return data

    logging.error(('data file not available'))

def display_graph():
    pass


from decimal import Decimal


def add_change_from(df,data, max=True):
    arr = numpy.nanmax(data.beforedata, axis=0)
    if max:
        ndat = -100 + data.beforedata.iloc[-1] / arr * 100
    else:
        ndat = data.beforedata.iloc[-1] / arr * 100 - 100

    ndat = ndat[df.columns]
    ndat = ndat.apply(lambda x: "{:.2f}".format(x) + '%')
    ndat = ndat.rename('Change from ' + 'max' if max else 'min')
    df = df.append(ndat)
    return df

d = {
        'K': 3,
        'M': 6,
        'B': 9,
        'T': 12
}

# the cols are final...
def text_to_num(text):
    if text[-1] in d:
        num, magnitude = text[:-1], text[-1]
        return Decimal(num) * 10 ** d[magnitude]
    else:
        return Decimal(text)


def human_to_int(s, orig, ret_nan=True):
    try:
        return text_to_num(s)
    except:
        if 1:
            return numpy.NaN



def convert_to_dec(df):
    return df.apply(lambda x: [(human_to_int(str(z).replace('%', ''), z, type(z) == str)) for z in x], raw=True).astype(
        float)


def add_target_price_change(df):
    dff = convert_to_dec(convert_to_dec(df)).astype(float)
    x = dff.loc['Target Price', :] / dff.loc['Price', :] * 100 - 100
    x.name = 'Target Price Change'
    df = df.append(x)

    return df


def highlight_it(df):
    dff = convert_to_dec(convert_to_dec(df)).astype(float)
    import numpy as np

    def highlight_max(x, color='green', colormin='blue'):
        z = np.where(x == np.nanmax(x.to_numpy()), f"color: {color};", None)
        q = np.where(x == np.nanmin(x.to_numpy()), f"color: {colormin};", None)
        return np.where(z != None, z, q)

    return df.style.apply(lambda x: dff.transpose().apply(highlight_max, axis=0).transpose(), axis=None)


def calc_closeness(dat, ski=1, interval=30):
    from numpy.lib.stride_tricks import sliding_window_view
    import numpy as np
    z = sliding_window_view(dat, window_shape=(2, 1))
    percchange = np.apply_along_axis(lambda x: float(x[1] / x[0] * 100), 2, z)

    percchange = percchange.reshape(percchange.shape[:-1])

    avgofinterval = np.average(sliding_window_view(percchange, window_shape=(interval, 1)), axis=2)
    arr = avgofinterval.reshape(avgofinterval.shape[:-1])
    from itertools import product
    from numpy import linalg as LA

    zz = np.array([[LA.norm(arr[:, x] - arr[:, y], 2) for x in range(arr.shape[1])] for y in range(arr.shape[1])])
    return pandas.DataFrame(zz, columns=dat.columns, index=dat.columns).rename_axis(columns={'Symbols': 'Closeness'})

def convert_df_dates(df):

    import matplotlib

    # assuming df is your DataFrame and df.index is the matplotlib dates
    df.index = df.index.to_series().apply(lambda x: matplotlib.dates.num2date(x).date())
    return df


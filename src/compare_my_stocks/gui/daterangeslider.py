import matplotlib
import pandas as pd
from PySide6.QtCore import Signal
from superqt.sliders._generic_range_slider import _GenericRangeSlider


class QDateRangeSlider(_GenericRangeSlider[float]):
    dateValueChanged = Signal(tuple)

    def __init__(self,*args, **kw):
        self.start=None
        self.end=None
        self.freq='D'
        self.fmt='%Y-%m-%d'
        super(QDateRangeSlider, self).__init__(*args, **kw)
        self.valueChanged.connect(self.my_val_change)


    def update_prop(self):
        for  name in ["fmt","freq"]:
            setattr(self,name,self.property(name))

    def update_obj(self):
        if self.start==None and self.end==None:
            return True
        self.date_range = [(x.to_pydatetime()) for x in pd.date_range(start=self.start, end=self.end, freq=self.freq)]
        self.options= [matplotlib.dates.date2num(y) for y in self.date_range]
        self._value= [min(self.options),max(self.options)]
        self._setPosition([min(self.options), max(self.options)])
        self.setRange(min(self.options),max(self.options))


        self.setSingleStep((self.options[1] - self.options[0]))
        self.setPageStep((self.options[5] - self.options[0]))



    def my_val_change(self,val):
        self.dateValueChanged.emit( [matplotlib.dates.num2date(x) for x in val])

    @property
    def datevalue(self):
        return matplotlib.dates.num2date([matplotlib.dates.num2date(x) for x in self.value])

    @datevalue.setter
    def datevalue(self,val):
        super(QDateRangeSlider, self).setValue(tuple([matplotlib.dates.date2num(x) for x in val]))

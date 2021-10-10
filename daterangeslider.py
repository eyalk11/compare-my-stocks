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
        #_DateMixin.__init__(self)#datetime.timdelta(days=1),datetime.timedelta(days=5))

        #hh=self.property('end')
        #super(QDesignerPropertyEditorInterface,self).__init__(*args, **kw)

    def update_prop(self):
        for  name in ["fmt","freq"]:
            setattr(self,name,self.property(name))
        #self.start=self.start.toPython()
        #self.update_obj()

    def update_obj(self):
        if self.start==None and self.end==None:
            return True
        self.date_range = [(x.to_pydatetime()) for x in pd.date_range(start=self.start, end=self.end, freq=self.freq)]
        self.options= [matplotlib.dates.date2num(y) for y in self.date_range]
        self._value= [min(self.options),max(self.options)]
        self._setPosition([min(self.options), max(self.options)])
        self.setRange(min(self.options),max(self.options))
        #self.setMinimum()
        #self.setinterval(self.date_range[1] - self.date_range[0])

        self.setSingleStep((self.options[1] - self.options[0]))
        self.setPageStep((self.options[5] - self.options[0]))

        #self.setvalue((min(self.date_range), max(self.date_range)))
        #self.options = [(item.strftime(self.fmt),item) for item in self.date_range]


    def my_val_change(self,val):
        self.dateValueChanged.emit( [matplotlib.dates.num2date(x) for x in val])

    @property
    def datevalue(self):
        return matplotlib.dates.num2date([matplotlib.dates.num2date(x) for x in self.value])
    #def valueChanged(self):
    #    return
    #self.value
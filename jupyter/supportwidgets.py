from datetime import datetime

from ipywidgets import SelectMultiple, Combobox, HBox, VBox
import ipywidgets as widgets
from common.common import Types
from IPython.core.display import display
from ipywidgets import Layout, Button, Box, Label, IntSlider
from jupyter.widgets import DateRangePicker

from engine.compareengine import CompareEngine

SELECT_BY_STOCKS = 'Select by stocks'

SELECT_BY_GROUP = 'Select by group'

rad=widgets.RadioButtons(
    options=['PRICE', 'VALUE', 'PROFIT','TOTPROFIT',"THEORTICAL_PROFIT"],
#    value='pineapple', # Defaults to 'pineapple'
#    layout={'width': 'max-content'}, # If the items' names are long
    description='Main',
    disabled=False)

rad2=widgets.RadioButtons(
    options=['RELTOMAX', 'PRECENTAGE', 'ABS','DIFF'],
    value='ABS', # Defaults to 'pineapple'
#    layout={'width': 'max-content'}, # If the items' names are long
    description='Sec',
    disabled=False)



col_item_layout = Layout(
        display='inline-flex',
        flex_flow='column',
        align_items='flex-start',
        width='50%'
    )


unite=widgets.Checkbox(
    description='Unite groups' ,value=False)
autoupd=widgets.Checkbox(
    description='Select by groups' ,value=False)
rad3=widgets.RadioButtons(
    options=[SELECT_BY_GROUP, SELECT_BY_STOCKS])


form_item_layout = Layout(
    display='flex',
    flex_flow='row',
    justify_content='space-between'
)



to_show=False




def dialog(gg):


    def myf(dl, ft,com,mn,numit,unite,rad3,dt2):
        #breakpoint()
        t = Types.__getattribute__(Types, dl) | Types.__getattribute__(Types, ft)
        gg.compare_with = com
        if gg.compare_with:
            gg.type =t | Types.COMPARE
        else:
            gg.type = t

        gg.valuerange=mn
        gg.numrange=numit
        gg.fromdate=dt2[0].to_pydatetime()
        gg.todate=dt2[1].to_pydatetime()

        #stockl.options= get_options_from_groups(cb)
        #stockl.value=stockl.options
        # if cb=='ALL':
        #     gg.groups = None
        # else:
        #     gg.groups= [cb]
        gg.update_graph()
        return 1

    def show_hide(b):
        global to_show
        gg.show_hide(to_show)
        to_show=not to_show



    def observe_group(change):

        if  'index' in change.new:
            #print(change.new)
            ls= change.new['index']
            value = [d.options[x] for x in ls]
        else:
            value=change.new

        stockl.options= get_options_from_groups(value)
        stockl.value=stockl.options
        if rad3.value== SELECT_BY_GROUP:
            # updateall(dl=rad.value,
            #           ft=rad2.value,
            #           com=comp.value,
            #           mn=mn.value,
            #           numit=numit.value, cb=d.value,
            #           unite=unite.value,rad3=rad3.value,dt2=dd.value)
            gg.groups = value
            gg.update_graph() #assuming rad3 updated it
            #breakpoint()
        pass

    #MyGraphGen.Groups.keys()
    d = SelectMultiple(options=list(CompareEngine.Groups.keys()), value=gg.groups if gg.groups != None else list(), description=' ')
    d.observe(observe_group,names='value')
    stockl=SelectMultiple(options=list(get_options_from_groups(d.value)) ,layout=Layout(flex='3 0 auto',display='inline-flex',flex_flow='row wrap', height='90%',
                                                                                        justify_content='flex-start', align_items='flex-start'))
    # stockl = SelectMultiple(options=list(get_options_from_groups(d.value)),
    #                         layout=Layout(flex='3 0 auto', display='inline-block',object_fit='fill', height='100%',
    #                                     ))
    #comp = Combobox(options=list(), ensure_option=False, placeholder='Choose stock', description=' ')
    addbox=Combobox(options=list(), ensure_option=False, placeholder='Choose stock', description=' ',layout=Layout(flex='1 1 auto',display='inline-flex',flex_flow='column wrap', align_items='flex-start'))
    comp=Combobox(options=list(gg.cols), ensure_option=False,placeholder='Choose stock',description=' ')
    mn=IntSlider(min=-10000, max=10000,description =' ')

    numit=IntSlider(min=0, max=100, description= ' ')





    b = Button(description='HideShow')
    b.on_click(show_hide)
    b_select_all = Button(description='All')
    def upd_all(x):
        d.options=d.value
    b.on_click(  upd_all)
    b_update = Button(description='Update')
    #items = [widgets.Button(description='>'), widgets.Button(description='<'), widgets.Button(description='Reset')]
    gb = widgets.GridBox([b,b_select_all,b_update], layout=widgets.Layout(grid_template_rows="repeat(3, 50px)"))

    mini_form_items=[Box([Label(value='Filter On Max'), mn ], layout=form_item_layout),
        Box([Label(value='Num Items Price'),numit ], layout=form_item_layout),
        Box([Label(value='Group'), d], layout=form_item_layout),
                     Box([Label(value='Compare with'), comp], layout=form_item_layout)]

    minibox= Box(mini_form_items, layout=Layout(
        display='flex',
        flex_flow='column',
        align_items='stretch',
        width='90%'
    ))

    dd = DateRangePicker(start='1/1/2020', end=datetime.now(), freq='1d')
    #temp=#SelectMultiple(options=list(),layout=Layout(width='30%'))


    form_items = [
        HBox([VBox([dd.slider_start,dd.slider_end],layout=Layout(display='flex',  flex_flow='rows',
        align_items='stretch',width='100%')),minibox], layout=form_item_layout),
        Box([rad,rad2,gb], layout=form_item_layout),
        HBox([unite,rad3])
    ]

    mbox= Box(form_items, layout=Layout(
        display='flex',
        flex_flow='column',
        align_items='stretch',
        width='90%'
    ))
    stock_shown=SelectMultiple(options=list(),layout=Layout(display='flex',align_self='flex-start',flex_flow='columns nowrap',justify_content='flex-start')) #,layout=Layout(flex='1 1 auto',display='inline-flex',flex_flow='row wrap',  height='100%',align_items='stretch'))
    butl=Layout(width='35px',justify_content='center')
    items = [widgets.Button(description='>',layout=butl), widgets.Button(description='<',layout=butl), widgets.Button(description='R',layout=butl)]
    gb2 = widgets.VBox(items,layout=Layout(display='flex',
        flex_flow='column',
        align_items='stretch',
        width='100%')) #widgets.GridBox(items, layout=widgets.Layout(grid_template_rows="repeat(3, 50px)",width='30px',height='100px',justify_items='center'))
    #gb3=widgets.GridBox([widgets.Label(description=' '),gb2,widgets.Label(description= ' ')], layout=widgets.Layout(grid_template_columns="1px 40px 1px", grid_template_rows="repeat(3, 100px)",grid_gap="0px 0px",width='50px',justify_items='center'))

    bb=Box([addbox,widgets.Button(description='Add')],layout=Layout(display='inline-flex',flex_flow='row',width='300px'))
    bestlt=layout=Layout(display='grid', grid_template_columns ='55% 400px 50px 400px' , border='solid 2px',height='300pt',width='100%' )
    form =  HBox([mbox, widgets.Box([stockl,bb],layout=col_item_layout),gb2,stock_shown],
                 layout=Layout(display='flex',height='300pt',width='100%',justify_content='flex-start',align_items='stretch'))
    #form = HBox([mbox, widgets.Box([stockl, bb], layout=col_item_layout), gb2, stock_shown],                layout=bestlt)

    i = widgets.interactive(myf,
                            dl=rad,
                            ft=rad2,
                            com=comp,
                            mn=mn,
                            numit=numit,
                            unite=unite,
                            rad3=rad3,
                            dt2=dd
                            )

    display(form)
    t=1
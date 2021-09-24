from ipywidgets import interact, interactive, fixed, interact_manual, SelectMultiple, Combobox, HBox
import ipywidgets as widgets
from getpositionsgraph import Types
from IPython.core.display import display
from getpositionsgraph import MyGraphGen
from ipywidgets import Layout, Button, Box, FloatText, Textarea, Dropdown, Label, IntSlider

rad=widgets.RadioButtons(
    options=['PRICE', 'VALUE', 'PROFIT'],
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


form_item_layout = Layout(
    display='flex',
    flex_flow='row',
    justify_content='space-between'
)



to_show=False

def dialog(gg):
    def myf(dl, ft,cb,com,mn,numit):
        t = Types.__getattribute__(Types, dl) | Types.__getattribute__(Types, ft)
        gg.compare_with = com
        if gg.compare_with:
            gg.type =t | Types.COMPARE
        else:
            gg.type = t
        gg.groups= cb
        gg.mincrit=mn
        gg.maxnum=numit

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

    def get_options_from_groups(ls):
        s=set()
        for g in ls:
            s=s.union( set(gg.Groups[g] ))
        return list(s)

    def observe_group(change):
        stockl.options= get_options_from_groups(change.owner.value)
        stockl.value=stockl.options

    d = SelectMultiple(options=list(MyGraphGen.Groups.keys()), value=gg.groups if gg.groups!=None else list(MyGraphGen.Groups.keys()),description=' ')
    d.observe(observe_group)
    stockl=SelectMultiple(options=list(get_options_from_groups(d.value)) ,layout=Layout(flex='3 0 auto',display='inline-flex',flex_flow='row wrap', height='100%',align_items='stretch'))
    # stockl = SelectMultiple(options=list(get_options_from_groups(d.value)),
    #                         layout=Layout(flex='3 0 auto', display='inline-block',object_fit='fill', height='100%',
    #                                     ))

    comp=Combobox(options=list(gg.cols), ensure_option=False,placeholder='Choose stock',description=' ')
    mn=IntSlider(min=-10000, max=10000,description =' ')
    numit=IntSlider(min=0, max=100, description= ' ')

    i = widgets.interactive(myf,
                            dl=rad,
                            ft=rad2,
                            cb=d,
                            com=comp,
                            mn=mn,
                            numit=numit

                            )


    b = Button(description='HideShow')
    b.on_click(show_hide)
    form_items = [
        Box([Label(value='Filter On Max'), mn ], layout=form_item_layout),
        Box([Label(value='Num Items Price'),numit ], layout=form_item_layout),
        Box([Label(value='Group'), d], layout=form_item_layout),
        Box([Label(value='Compare with'), comp], layout=form_item_layout),
        Box([rad,rad2,b], layout=form_item_layout)
    ]

    mbox= Box(form_items, layout=Layout(
        display='flex',
        flex_flow='column',
        align_items='stretch',
        width='50%'
    ))
    #select=
    form =  HBox([mbox, stockl], layout=Layout(display='flex',border='solid 2px',width='100%',height='300pt',align_items='stretch') )


    display(form)
    t=1
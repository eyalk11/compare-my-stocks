
from datetime import datetime
from io import StringIO
from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout
from pandas import Timestamp

from common.simpleexceptioncontext import simple_exception_handling
from config import config
from qtvoila import QtVoila
import pandas as pd
from typing import List
from common.common import unlocalize_it 

from dataclasses import dataclass
from gui.jupytercommon import JupyterCommonHandler

@dataclass
class DfDesc:
    df_name: str
    df_desc: str
    df: pd.DataFrame

class VoilaStatus(JupyterCommonHandler):

    @simple_exception_handling("generate dialog")
    def generate_dialog(self,dfs : List[DfDesc]):
    # Create a QtVoila instance
        qtvoila = QtVoila()

        qtvoila.max_voila_wait = config.Voila.MaxVoilaWait
        self.resolve_voila(qtvoila)
        for k in dfs:
            qtvoila.add_notebook_cell(dict(), f"#{k.df_name}",cell_type='markdown')
            qtvoila.add_notebook_cell(dict(), f"{k.df_desc}",cell_type='markdown')
            #use buffer 
            #df remove timezone from al
            #df = k.df.applymap(lambda x: unlocalize_it(x) if type(x) is datetime else x )
            df = k.df.applymap(lambda x: unlocalize_it(x) if type(x) is Timestamp else x)
            dic=df.to_dict ()
            import pickle
            buffer=pickle.dumps(dic)
            code=f'''
            from io import StringIO
            import pandas as pd
            from ipydatagrid import DataGrid
import pickle
dic=pickle.loads({str(buffer)})
            df = pd.DataFrame(dic)
            dd=DataGrid(df)
            dd.auto_fit_columns=True
            dd
            '''
        # Add a notebook cell for example
            qtvoila.add_notebook_cell(dict(), code )

        # Create a dialog
        dialog = QDialog()
        dialog.setMinimumWidth(1000)
        dialog.setMinimumHeight(400)

        # Create and set layout for the dialog
        layout = QVBoxLayout(dialog)
        layout.addWidget(qtvoila)

        # Add Close Button
        btn_close = QPushButton("Close", dialog)
        btn_close.pressed.connect(dialog.close)
        layout.addWidget(btn_close)

        qtvoila.run_voila()


        # Show the dialog
        try:
            dialog.exec()
        finally:
            qtvoila.close_renderer()

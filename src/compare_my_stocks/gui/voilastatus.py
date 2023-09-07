
from io import StringIO
from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout

from common.simpleexceptioncontext import simple_exception_handling
from config import config
from qtvoila import QtVoila
import pandas as pd
from typing import List

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

        qtvoila.max_voila_wait = config.Voila.MAX_VOILA_WAIT
        self.resolve_voila(qtvoila)
        for k in dfs:
            qtvoila.add_notebook_cell(dict(), f"#{k.df_name}",cell_type='markdown')
            qtvoila.add_notebook_cell(dict(), f"{k.df_desc}",cell_type='markdown')
            #use buffer 
            buffer = StringIO()
            k.df.to_json(buffer)
            code='''
            from io import StringIO
            import pandas as pd
            from ipydatagrid import DataGrid
            json = StringIO( """{}""")
            df = pd.read_json(json)
            DataGrid(df)
            ''' .format(buffer.getvalue())
        # Add a notebook cell for example
            qtvoila.add_notebook_cell(dict(), code )

        # Create a dialog
        dialog = QDialog()
        dialog.setMinimumWidth(600)
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

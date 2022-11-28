import os

from setuptools import setup, find_packages
import pathlib

import pkg_resources
import setuptools

MYPROJ='compare_my_stocks' #should be same as in config.py
dir=os.path.join(os.path.expanduser("~"), "." + MYPROJ)

setup(
    name='compare-my-stocks',
    version='1.0.0',
    packages=find_packages(),
    data_files=[
        ( dir , ["compare_my_stocks/data/myconfig.py" , "compare_my_stocks/data/mygroups.json"]),
        ( "compare_my_stocks/gui" , ["compare_my_stocks/gui/mainwindow.ui"])
    ],
    entry_points={'console_scripts': ['compare-my-stocks = compare_my_stocks.__main__:main']},
    url='https://github.com/eyalk11/compare-my-stocks',
    license='GNU Affero General Public License v3.0 ',
    author='Eyal Karni',
    author_email='eyalk5@gmail.com',
    description='A system for visualizing interesting stocks/etf/crypto using matplotlib and QT. Synchronizes transaction data from MyStocksProtoflio.  ',
    install_requires=
    [
"Flask==2.0.2",
"numpy==1.22.0",
"requests==2.26.0",
"PySide6==6.2.0",
"matplotlib==3.5.1",
"pandas==1.3.5",
"python-dateutil==2.8.2",
"pytz==2021.3",
"json_editor @ git+https://github.com/eyalk11/json-editor.git#egg=json_editor-1.0.0",
"investpy @ git+https://github.com/eyalk11/investpy.git#egg=investpy-1.0.7a",
"superqt==0.2.5.post1",
"mplcursors==0.4",
"Django==3.2.9",
"nbmanager @ git+https://github.com/jupyter/nbmanager.git",
"ib_insync",
"Pyro5",
"ibflex"
    ],
    include_package_data=True,
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
)

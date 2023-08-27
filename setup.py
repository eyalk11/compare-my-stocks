import os

from setuptools import setup, find_packages

minimal_reqs = [
    'dacite~=1.8.0',
    'ruamel.yaml'
    ,'numpy==1.22.0'
    ,'pandas==1.3.5',
    'django',
    'colorlog'
]

data_files = []
for root, dirs, files in os.walk("src/compare_my_stocks/data"):
    for file in files:
        path = os.path.join(root, file)
        data_files.append(path)

with open('requirements.txt') as f:
    requirements = f.read().splitlines()
    requirements = [r for r in requirements if not r.startswith('git+') and r not in minimal_reqs]

setup(
    name='compare-my-stocks',
    version='1.0.0',
    packages=find_packages(where="src"),
    data_files=[
        ( "compare_my_stocks/data" , data_files),
        ( "compare_my_stocks/gui" , ["src/compare_my_stocks/gui/mainwindow.ui"]),
        ( "compare_my_stocks/common" , ["src/compare_my_stocks/common/impacketLICENSE"])
    ],
    entry_points={'console_scripts': ['compare-my-stocks = compare_my_stocks.__main__:main']},
    url='https://github.com/eyalk11/compare-my-stocks',
    license='GNU Affero General Public License v3.0 ',
    author='Eyal Karni',
    author_email='eyalk5@gmail.com',
    description='A system for visualizing interesting stocks/etf/crypto using matplotlib and QT. Synchronizes transaction data from MyStocksProtoflio.  ',
    install_requires=minimal_reqs,
    extra_require=
    {
        "full": [
"json_editor @ git+https://github.com/eyalk11/json-editor.git#egg=json_editor-1.0.0",
"nbmanager @ git+https://github.com/jupyter/nbmanager.git",
    ]+requirements
    }
        ,
    package_dir={'': 'src'},
    include_package_data=True,
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
)

import os

from setuptools import setup, find_packages
print('setup.py is deprecated. Dont use it.')

minimal_reqs = [
    'dacite~=1.8.0',
    'ruamel.yaml'
    ,'numpy==1.22.4'
    ,'pandas==1.5.3',
    'django',
    'colorlog'
    'pydantic',
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
version = "1.0.7",
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
    description='A system for visualizing interesting stocks. Has powerful comparison capabilities and works seamlessly with your jupyter notebook.   Written in QT with matplotlib.',
    install_requires=minimal_reqs,
    extra_require=
    {
        "full": requirements
    }
        ,
    package_dir={'': 'src'},
    include_package_data=True,
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
)

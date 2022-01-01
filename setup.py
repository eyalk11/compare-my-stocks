from setuptools import setup

setup(
    name='compare-my-stocks',
    version='1.0.0',
    packages=['ib', 'input', 'engine', 'processing'],
    url='https://github.com/eyalk11/compare-my-stocks',
    license='GNU Affero General Public License v3.0 ',
    author='Eyal Karni',
    author_email='eyalk5@gmail.com',
    description='A system for visualizing interesting stocks/etf/crypto using matplotlib and QT. Synchronizes transaction data from MyStocksProtoflio.  '
)

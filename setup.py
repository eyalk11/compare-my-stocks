from setuptools import setup, find_packages
import pathlib

import pkg_resources
import setuptools

with pathlib.Path('requirements.txt').open() as requirements_txt:
    install_requires = [
        str(requirement)
        for requirement
        in pkg_resources.parse_requirements(requirements_txt)
    ]

setup(
    name='compare_my-stocks',
    version='1.0.0',
    packages=find_packages(),

    entry_points={'console_scripts': ['compare_my_stocks = compare_my_stocks.__main__:main']},
    url='https://github.com/eyalk11/compare-my-stocks',
    license='GNU Affero General Public License v3.0 ',
    author='Eyal Karni',
    author_email='eyalk5@gmail.com',
    description='A system for visualizing interesting stocks/etf/crypto using matplotlib and QT. Synchronizes transaction data from MyStocksProtoflio.  ',
install_requires=install_requires
)

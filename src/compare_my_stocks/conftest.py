import pytest
def pytest_sessionstart():
    pass
def pytest_runtest_setup(item):
    # called for running each test in 'a' directory
    print("setting up", item)

def pytest_sessionfinish():
    # called for running each test in 'a' directory
    print("ended")
    from runsit import MainClass

    MainClass.killallchilds(tolog=False)

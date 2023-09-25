from common.composition import C


def f(a,b,c):
    return (b)
def g(b,c):
    print(c)
    return (b)
def h(b,c):
    print(c)
    return (b)


def test_curry():
    x=  (C // h // g // f @ (3, 7,8))
    assert x==7


def test_col():
    x= C/[1,2,3] << '-> x*2'
    assert x==[2,4,6]
def f(a,b,c):
    pass
from multiprocessing import Pool
import os

def test_func(x):
    return x*x

if __name__ == '__main__':
    with Pool(4) as p:
        print(p.map(test_func, range(10)))
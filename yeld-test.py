# A Python program to generate squares from 1
# to 100 using yield and therefore generator

# An infinite generator function that prints
# next square number. It starts with 1
from time import sleep

from threading import Thread
def nextSquare(s, d):
    i = s;

    # An Infinite loop to generate squares
    while True:
        yield i * i
        i += 1  # Next execution resumes
        sleep(d)
    # from this point


def doIt(p, s, d):
    for num in nextSquare(s, d):
        if num > 1000:
            break
        print(p, num)


t1 = Thread(target=doIt, args=("1", 1, 1,))
t1.start()
t2 = Thread(target=doIt, args=("2", 6, 3,))
t2.start()
t1.join()
t2.join()
print('end..............')




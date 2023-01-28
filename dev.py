from threading import Timer


class Test:
    def __init__(self):
        self.name = 'Marco'


def loop(a):
    t = Timer(2, loop, [a]).start()
    print(a.name)


marco = Test()
loop(marco)
print()

from threading import Timer
import os


class IntervalTask:
    def __init__(self, interval, function, arguments):
        self.__run = False
        self.__arguments = arguments
        self.__interval = interval
        self.__function = function
        self.__timer = None

    @property
    def active(self):
        return self.__run

    def set_interval(self, new_interval):
        self.__interval = new_interval

    def start(self):
        self.__run = True
        self.loop(self.__function, self.__arguments)

    def stop(self):
        self.__run = False

    def loop(self, function, arguments):
        if not self.__run:
            return

        timer = Timer(self.__interval, self.loop, [function, arguments]).start()
        if not self.__timer:
            self.__timer = timer

        try:
            function(*arguments)
        except Exception as e:
            self.__run = False
            raise e

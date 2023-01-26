from threading import Timer
from libraries import Logger


class Task:
    def __init__(self, interval):
        self.run = False
        self.interval = interval
        self.__timer = None
        self.__logger = Logger.Logger(self.__class__.__name__)

    def logic(self):
        raise Exception("Needs to be implemented by a child class")

    def set_interval(self, new_interval):
        self.interval = new_interval

    def start(self):
        self.run = True
        self.loop()

        return self

    def stop(self):
        self.run = False

    def loop(self):
        if not self.run:
            return

        timer = Timer(self.interval, self.loop, []).start()
        if not self.__timer:
            self.__timer = timer

        try:
            self.logic()
        except Exception as e:
            self.run = False
            raise e

    def get_config(self):
        def contains_name(pair):
            key, value = pair
            # if self.__class__.__name__ in key:
            if "__" in key:
                return False
            else:
                return True

        return dict(filter(contains_name, self.__dict__.items()))

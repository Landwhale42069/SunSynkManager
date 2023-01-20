from threading import Timer
import os


class IntervalTask:
    def __init__(self, interval, function, arguments):
        self.__run = False
        self.__arguments = arguments
        self.__interval = interval
        self.__function = function
        self.__timer = None

        self.__logger = None

    @property
    def name(self):
        return self.__function.__name__

    @property
    def active(self):
        return self.__run

    @property
    def logs(self):
        if self.__logger is not None:
            _dir = self.__logger.directory
            logfiles = []
            for file in os.listdir(_dir):
                if self.__function.__name__ in file:
                    with open(os.path.join(_dir, file), 'r') as f:
                        logfiles.append({
                            'name': file,
                            'content': f.read(),
                        })

            return logfiles
        else:
            return []

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
            self.__logger = function(*arguments)
        except Exception as e:
            self.__run = False
            raise e

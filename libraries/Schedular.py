from threading import Timer


class IntervalTask:
    def __init__(self, interval, function, arguments):
        print('IntervalTask constructor')
        self.conf = {
            'run': False,
            'arguments': arguments,
            'interval': interval,
            'function': function,
        }

    def start(self):
        print('starting')

        def temp_function(conf):
            Timer(interval, temp_function, [conf])

            function()

        temp_function(self.conf)

        return self

    def stop(self):
        print('stopping')

        return self

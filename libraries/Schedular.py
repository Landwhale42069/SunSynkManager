from threading import Timer
from libraries import Logger


class Task:
    task_id_counter = 0

    def __init__(self, interval, name, description):
        self.name = name
        self.description = description
        self.task_id = self.task_id_counter
        Task.task_id_counter += 1
        self.config__run = False
        self.config__interval = interval
        self.__timer = None
        self.__logger = Logger.Logger(self.__class__.__name__)

        self.outputs = []
        self.additional_attributes = []

    def logic(self):
        raise Exception("Needs to be implemented by a child class")

    def set_interval(self, new_interval):
        self.config__interval = new_interval

    def start(self):
        self.config__run = True
        self.loop()

        return self

    def stop(self):
        self.config__run = False

    def loop(self):
        if not self.config__run:
            return

        timer = Timer(self.config__interval, self.loop, []).start()
        if not self.__timer:
            self.__timer = timer

        try:
            self.logic()
        except Exception as e:
            self.config__run = False
            raise e

    def get_output(self):
        return self.outputs

    def __get_attributes(self, prefix):
        return_dict = {}
        for attribute in self.__dict__:
            if prefix in attribute:
                new_key = attribute.split(prefix)[1]
                return_dict[new_key] = self.__dict__[attribute]

        for attribute in self.additional_attributes:
            if prefix in attribute:
                new_key = attribute.split(prefix)[1]
                return_dict[new_key] = self.__getattribute__(new_key)

        return return_dict

    def __set_attributes(self, prefix, attributes):
        for key in attributes:
            if f"{prefix}{key}" in self.__dict__:
                attribute = [_attribute for _attribute in self.__dict__ if f"{prefix}{key}" in _attribute][0]
                self.__dict__[attribute] = attributes[key]

        for key in self.additional_attributes:
            actual_key = key.split(prefix)[1]
            if actual_key in attributes:
                try:
                    self.__getattribute__(actual_key)
                    self.__setattr__(actual_key, attributes[actual_key])
                    self.__logger.info(f"\tSet special property {actual_key}, to {attributes[actual_key]}")
                except AttributeError or KeyError as e:
                    self.__logger.warning(f"\tTried to set a property that wasn't supposed to be set, {self}: {actual_key}")

    def get_config(self):
        return self.__get_attributes('config__')

    def set_config(self, config):
        return self.__set_attributes('config__', config)

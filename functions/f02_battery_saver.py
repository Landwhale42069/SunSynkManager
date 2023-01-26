from datetime import datetime
from libraries import Logger
from libraries.Schedular import Task


class BatterySaverTask(Task):
    def __init__(self, arguments):
        self._Task__logger = None
        super().__init__(10, 'Battery Saver',
                         "Uses the charge rate of the inverter battery to estimate the future state of the battery, then disables controllable devices to correct")
        self.__arguments = arguments
        self.__arguments['loggers']['f02_battery_saver'] = self._Task__logger

        self.config__battery_Wh_capacity = 10800
        self.config__battery_safety = 30
        self.config__projected_duration = 2
        self.config__trigger_every = 30
        self.config__ideal_value = 40
        self.config__factor = 4

        self.__sample_buffer_size = 10
        self.__sample_buffer = [0] * self.__sample_buffer_size
        self.__trigger_count = self.config__trigger_every
        self.additional_attributes = [
            'config__sample_buffer_size'
        ]

        self.outputs = {
            'predictionPlot': {
                'type': 'Chart',
                'name': 'Prediction Plot',
                'content': {
                    'chart': {
                        'type': 'line'
                    },
                    'series': [{
                        'name': 'Battery Power',
                        'data': self.__sample_buffer
                    }],
                    'xaxis': {
                        'categories': [0-i for i in range(self.sample_buffer_size)]
                    }
                }
            }
        }

        self.disabled_devices = []

    @property
    def sample_buffer_size(self):
        return self.__sample_buffer_size

    @sample_buffer_size.setter
    def sample_buffer_size(self, new_sample_buffer_size):
        if new_sample_buffer_size <= 0:
            return

        difference = self.sample_buffer_size - new_sample_buffer_size
        if difference > 0:
            self.__sample_buffer = self.__sample_buffer[difference::]
        elif difference < 0:
            self.__sample_buffer = [0] * abs(difference) + self.__sample_buffer

        self.__sample_buffer_size = new_sample_buffer_size

    def logic(self):
        self._Task__logger.update_file_handler()
        battery_soc = self.__arguments['registers']['battery_soc']
        battery_power = self.__arguments['registers']['battery_power']

        geyser_kitchen = self.__arguments['devices']['geyser_kitchen']
        geyser_bathroom = self.__arguments['devices']['geyser_bathroom']
        pool_pump = self.__arguments['devices']['pool_pump']

        # Buffer battery power history
        self.__sample_buffer.append(battery_power.get_value())
        self.__sample_buffer.pop(0)

        if not self.__trigger_count < 1:
            self.__trigger_count -= 1

            # New X Data
            self.outputs['predictionPlot']['content']['series'] = [{
                            'name': 'Battery Power',
                            'data': self.__sample_buffer
                        }]
        else:
            self._Task__logger.info(f"------------------------------------------")
            __trigger_count = self.config__trigger_every

            current_percent = battery_soc.get_value()
            average_battery_power = sum(self.__sample_buffer) / len(self.__sample_buffer)
            power_left = (current_percent / 100) * self.config__battery_Wh_capacity

            expected_percentage_left = ((
                                                    power_left - average_battery_power * self.config__projected_duration) / self.config__battery_Wh_capacity) * 100

            self._Task__logger.debug(f"\tCurrent       | {round(current_percent, 2):>20} %")
            self._Task__logger.debug(f"\tAverage usage | {round(average_battery_power, 2):>20}")
            self._Task__logger.debug(f"\tExpected left | {round(expected_percentage_left, 2):>20} %")

            missing_percentage = self.config__ideal_value - expected_percentage_left
            # Power to drop = missing power (Wh) * time to recover (1/h) * ratio
            power_to_drop = (missing_percentage / 100) * self.config__battery_Wh_capacity * (
                        1 / self.config__projected_duration) * self.config__factor

            self._Task__logger.info(f"Going to try to drop {round(power_to_drop, 2)} W")

            if power_to_drop > 0:

                _device = geyser_kitchen
                _usage = _device.get_usage()
                if power_to_drop > _usage:
                    self._Task__logger.debug(f"{_device.name} is using {_usage} W, turning off")
                    power_to_drop -= _usage
                    _device.shutdown()

                _device = geyser_bathroom
                _usage = _device.get_usage()
                if power_to_drop > _usage:
                    self._Task__logger.debug(f"{_device.name} is using {_usage} W, turning off")
                    power_to_drop -= _usage
                    _device.shutdown()

                _device = pool_pump
                _usage = _device.get_usage()
                if power_to_drop > _usage:
                    self._Task__logger.debug(f"{_device.name} is using {_usage} W, turning off")
                    power_to_drop -= _usage
                    _device.shutdown()

            else:

                _device = geyser_kitchen
                _usage = _device.get_usage(if_on=True)
                if -power_to_drop > _usage:
                    self._Task__logger.debug(f"{_device.name} will use {_usage} W, turning on")
                    power_to_drop += _usage
                    _device.startup()

                try:

                    _device = geyser_bathroom
                    _usage = _device.get_usage(if_on=True)
                    _temp = float(_device.get('obj').get('params').get("currentTemperature"))
                    if -power_to_drop > _usage and _temp < 44.5:
                        self._Task__logger.debug(f"{_device.name} will use {_usage} W, turning on")
                        power_to_drop += _usage
                        _device.startup()
                except Exception as e:
                    self._Task__logger.warning(f"Error when trying to turn {geyser_bathroom.name} back on, {e}")

                _device = pool_pump
                _usage = _device.get_usage(if_on=True)
                _start = datetime.now().replace(hour=8, minute=30, second=0, microsecond=0)
                _end = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
                if -power_to_drop > _usage and _start < datetime.now() < _end:
                    self._Task__logger.debug(f"{_device.name} will use {_usage} W, turning on")
                    power_to_drop += _usage
                    _device.startup()

        self.outputs = {
            'predictionPlot': {
                'name': 'predictionPlot',
                'type': 'Chart',
                'content': {
                    'chart': {
                        'type': 'line'
                    },
                    'series': [{
                        'name': 'Battery Power',
                        'data': self.__sample_buffer
                    }],
                    'xaxis': {
                        'categories': [0-i for i in range(self.sample_buffer_size)]
                    }
                }
            }
        }

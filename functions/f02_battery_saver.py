from datetime import datetime
from libraries import Logger
from libraries.Schedular import Task


class BatterySaverTask(Task):
    def __init__(self, arguments):
        self._Task__logger = None
        super().__init__(10)
        self.__arguments = arguments
        self.__arguments['loggers']['f02_battery_saver'] = self._Task__logger

        self.battery_Wh_capacity = 10800
        self.battery_safety = 30
        self.projected_duration = 2
        self.trigger_every = 30
        self.ideal_value = 40
        self.factor = 4

        self.__sample_buffer_size = 10
        self.__battery_discharge_rate = [0] * self.__sample_buffer_size
        self.__trigger_count = self.trigger_every

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
            self.__battery_discharge_rate = self.__battery_discharge_rate[difference::]
        elif difference < 0:
            self.__battery_discharge_rate = [0]*abs(difference) + self.__battery_discharge_rate

        self.__sample_buffer_size = new_sample_buffer_size

    def logic(self):
        self._Task__logger.update_file_handler()
        battery_soc = self.__arguments['registers']['battery_soc']
        battery_power = self.__arguments['registers']['battery_power']

        geyser_kitchen = self.__arguments['devices']['geyser_kitchen']
        geyser_bathroom = self.__arguments['devices']['geyser_bathroom']
        pool_pump = self.__arguments['devices']['pool_pump']

        # Buffer battery power history
        self.__battery_discharge_rate.append(battery_power.get_value())
        self.__battery_discharge_rate.pop(0)

        if not self.__trigger_count < 1:
            self.__trigger_count -= 1

        else:
            self._Task__logger.info(f"------------------------------------------")
            __trigger_count = self.trigger_every

            current_percent = battery_soc.get_value()
            average_battery_power = sum(self.__battery_discharge_rate) / len(self.__battery_discharge_rate)
            power_left = (current_percent / 100) * self.battery_Wh_capacity

            expected_percentage_left = ((power_left - average_battery_power * self.projected_duration) / self.battery_Wh_capacity) * 100

            self._Task__logger.debug(f"\tCurrent       | {round(current_percent, 2):>20} %")
            self._Task__logger.debug(f"\tAverage usage | {round(average_battery_power, 2):>20}")
            self._Task__logger.debug(f"\tExpected left | {round(expected_percentage_left, 2):>20} %")

            missing_percentage = self.ideal_value - expected_percentage_left
            # Power to drop = missing power (Wh) * time to recover (1/h) * ratio
            power_to_drop = (missing_percentage/100) * self.battery_Wh_capacity * (1/self.projected_duration) * self.factor

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

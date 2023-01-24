from libraries import Logger
from datetime import datetime

__battery_Wh_capacity = 10800
__battery_safety = 30
__projected_duration = 2

__sample_history = 10
__trigger_every = 30
__trigger_count = __trigger_every

__battery_discharge_rate = [0]*__sample_history

__disabled_devices = []


def logic(state):
    global \
        __battery_Wh_capacity, __battery_safety, __battery_discharge_rate, \
        __trigger_every, __trigger_count, \
        __projected_duration, \
        __disabled_devices

    logger = Logger.Logger('f02_battery_saver')

    battery_soc = state.get('battery_soc')
    battery_power = state.get('battery_power')

    # Buffer battery power history
    __battery_discharge_rate.append(battery_power.get_value())
    __battery_discharge_rate.pop(0)

    if not __trigger_count < 1:
        __trigger_count -= 1

    else:
        logger.info(f"------------------------------------------")
        __trigger_count = __trigger_every

        current_percent = battery_soc.get_value()
        average_battery_power = sum(__battery_discharge_rate) / len(__battery_discharge_rate)
        power_left = (current_percent / 100) * __battery_Wh_capacity

        expected_percentage_left = ((power_left - average_battery_power * __projected_duration) / __battery_Wh_capacity) * 100

        logger.debug(f"\tCurrent       | {round(current_percent, 2):>20} %")
        logger.debug(f"\tAverage usage | {round(average_battery_power, 2):>20}")
        logger.debug(f"\tExpected left | {round(expected_percentage_left, 2):>20} %")

        missing_percentage = 40 - expected_percentage_left
        # Power to drop = missing power (Wh) * time to recover (1/h) * ratio
        power_to_drop = (missing_percentage/100) * __battery_Wh_capacity * (1/__projected_duration) * 4

        logger.info(f"Going to try to drop {round(power_to_drop, 2)} W")

        geyser_kitchen = state.get('geyser_kitchen')
        geyser_bathroom = state.get('geyser_bathroom')
        pool_pump = state.get('pool_pump')

        if power_to_drop > 0:

            _device = geyser_kitchen
            _usage = _device.get_usage()
            if power_to_drop > _usage:
                logger.debug(f"{_device.name} is using {_usage} W, turning off")
                power_to_drop -= _usage
                _device.shutdown()

            _device = geyser_bathroom
            _usage = _device.get_usage()
            if power_to_drop > _usage:
                logger.debug(f"{_device.name} is using {_usage} W, turning off")
                power_to_drop -= _usage
                _device.shutdown()

            _device = pool_pump
            _usage = _device.get_usage()
            if power_to_drop > _usage:
                logger.debug(f"{_device.name} is using {_usage} W, turning off")
                power_to_drop -= _usage
                _device.shutdown()

        else:

            _device = geyser_kitchen
            _usage = _device.get_usage(if_on=True)
            if -power_to_drop > _usage:
                logger.debug(f"{_device.name} will use {_usage} W, turning on")
                power_to_drop += _usage
                _device.startup()

            try:

                _device = geyser_bathroom
                _usage = _device.get_usage(if_on=True)
                _temp = float(_device.get('obj').get('params').get("currentTemperature"))
                if -power_to_drop > _usage and _temp < 44.5:
                    logger.debug(f"{_device.name} will use {_usage} W, turning on")
                    power_to_drop += _usage
                    _device.startup()
            except Exception as e:
                logger.warning(f"Error when trying to turn {geyser_bathroom.name} back on, {e}")

            _device = pool_pump
            _usage = _device.get_usage(if_on=True)
            _start = datetime.now().replace(hour=8, minute=30, second=0, microsecond=0)
            _end = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
            if -power_to_drop > _usage and _start < datetime.now() < _end:
                logger.debug(f"{_device.name} will use {_usage} W, turning on")
                power_to_drop += _usage
                _device.startup()

    state['loggers']['f02_battery_saver'] = logger


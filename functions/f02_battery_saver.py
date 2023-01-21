from libraries import Logger
from datetime import datetime

__battery_Wh_capacity = 10800
__battery_safety = 30
__projected_duration = 2

__sample_history = 10
__trigger_every = 10
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

        device_list = [
            state.get('geyser1'),
            state.get('geyser2'),
            # state.get('pool_pump'),
        ]

        if power_to_drop > 0:
            for _device in device_list:
                _expected_usage = _device.get_usage()

                # If the device's expected usage needs to be dropped, and the device isn't disabled
                if _expected_usage < power_to_drop and not __disabled_devices.__contains__(_device):
                    logger.info(f"{_device.name} is using ~{_expected_usage} W, turning it off")
                    power_to_drop -= _expected_usage
                    _device.shutdown()

                    if _device.device_id != '100178de05':
                        __disabled_devices.append(_device)
        else:
            restored_devices = []
            for _device in __disabled_devices:
                if _device.get_usage(if_on=True) == 0:
                    logger.info(f"{_device.name} isn't going to use power now... Resetting it's state")
                    _device.restore()
                    restored_devices.append(_device)

            for _device in restored_devices:
                __disabled_devices.pop(__disabled_devices.index(_device))

    state['loggers']['f02_battery_saver'] = logger


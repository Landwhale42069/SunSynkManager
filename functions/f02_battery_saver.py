from libraries import Logger

__battery_Wh_capacity = 10800
__battery_safety = 30

__sample_history = 10
__trigger_every = 10
__trigger_count = __trigger_every

__battery_discharge_rate = [0]*__sample_history


def logic(state):
    global \
        __battery_Wh_capacity, __battery_safety, __battery_discharge_rate, \
        __trigger_every, __trigger_count

    logger = Logger.Logger('f02_battery_saver')
    logger.info(f"------------------------------------------")

    battery_soc = state.get('battery_soc')
    battery_power = state.get('battery_power')

    # Buffer battery power history
    __battery_discharge_rate.append(battery_power.get_value())
    __battery_discharge_rate.pop(0)

    if __trigger_count < 1:
        __trigger_count = __trigger_every
    else:
        __trigger_count -= 1

        average_battery_power = sum(__battery_discharge_rate) / len(__battery_discharge_rate)
        power_left = (battery_soc.get_value() / 100) * __battery_Wh_capacity

        expected_percentage_left = ((power_left - average_battery_power * 2) / __battery_Wh_capacity) * 100
        factor = 3 * (1 - (expected_percentage_left - __battery_safety) / (100 - __battery_safety))

        device_list = [
            state.get('geyser1'),
            state.get('geyser2'),
            state.get('pool_pump'),
        ]

        logger.info(f"Factor of {factor}")
        logger.debug(f"\tCurrent %       {average_battery_power:>20}")
        logger.debug(f"\tAverage usage   {average_battery_power:>20}")
        logger.debug(f"\tExpected % left {expected_percentage_left:>20}")

        for i in range(int(factor)):
            if i < len(device_list):
                logger.debug(f"Disabling device {i + 1}")
                device = device_list[i]

                if device.switch == 'on':
                    logger.debug(f"{device.name} is on, turning off")
                    device.off()

                if device.switches:
                    for outlet in device.switches:
                        if outlet.get('switch') == 'on':
                            logger.debug(f"{device.name} outlet {outlet.get('outlet')} is on, turning off")
                            device.off(outlet.get('outlet'))

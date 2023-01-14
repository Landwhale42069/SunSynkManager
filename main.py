from libraries import Logger, eWeLink, Inverter, Loadshedding, Interface, Schedular

import time
from datetime import datetime, timedelta


def main():
    # Create and set static logger for Device and Register
    logger = Logger.Logger('SunSynk')
    eWeLink.Device.logger = logger
    Inverter.Register.logger = logger
    Loadshedding.Tracker.logger = logger
    Interface.WebAPI.logger = logger

    web_interface = Interface.WebAPI("interface")
    web_interface.startup()

    loadshedding = Loadshedding.Tracker("schedule.csv")

    # Define devices
    dryer = eWeLink.Device('100168b564')
    # geyser1 = eWeLink.Device('10017e9016')
    # geyser2 = eWeLink.Device('100178de05')
    # pool_pump = eWeLink.Device('1001793ec2')

    # stoep = eWeLink.Device('10012b9022')

    # Define registers
    # battery_soc = Inverter.Register(184, "Battery SOC", -1, "%")
    # battery_power = Inverter.Register(190, "Battery power", -1, "Watt")
    # grid_power = Inverter.Register(169, "Grid power", -1, "Watt")
    # load_power = Inverter.Register(178, "Load power", -1, "Watt")
    # pv1_power = Inverter.Register(186, "PV1 power", -1, "Watt")
    # pv2_power = Inverter.Register(187, "PV2 power", -1, "Watt")
    grid_status = Inverter.Register(194, "Grid Connected Status")

    # a = Schedular.IntervalTask(5, _print, ["something"])

    argument_dict = {
        'loadshedding': loadshedding,

        'dryer': dryer,

        'grid_status': grid_status,
    }

    t01_dryer_watchdog = Schedular.IntervalTask(60, f01_dryer_watchdog, [argument_dict])

    t01_dryer_watchdog.start()

    print()


def f01_dryer_watchdog(state):
    logger = Logger.Logger('f01_dryer_watchdog')

    loadshedding = state.get('loadshedding')
    loadshedding_ends = state.get('loadshedding_ends')
    grid_status = state.get('grid_status')
    dryer = state.get('dryer')

    loadshedding_status = loadshedding.get_next()
    currently_loadshedding = False
    if loadshedding_status:
        logger.debug(f"Current loadshedding status: {loadshedding_status}")
        ls_window_start = loadshedding_status['_start'] - timedelta(minutes=3)
        ls_window_end = loadshedding_status['_start'] + timedelta(minutes=60)
        currently_loadshedding = ls_window_start < datetime.now() < ls_window_end

        if currently_loadshedding and not loadshedding_ends:
            loadshedding_ends = ls_window_end

    grid_power = True if grid_status.get_value() == 1 else False

    logger.info(f"loadshedding: {loadshedding_status}")
    logger.info(f"grid_power: {grid_power}")
    logger.info(f"dryer_power: {dryer.power} W")
    logger.info(f"---------------------------")

    if not grid_power or currently_loadshedding:
        logger.info(f"grid: {grid_power}, loadshedding: {bool(currently_loadshedding)}")

        if dryer.switch == 'on':
            logger.info(f'Turning {dryer} off')
            dryer.off()
        else:
            logger.debug('Already off')

    elif (loadshedding_ends and datetime.now() > loadshedding_ends and grid_power) or (
            grid_power and not loadshedding_ends):
        loadshedding_ends = None

        if dryer.switch == 'off':
            logger.info(f'Turning {dryer} on')
            dryer.on()
        else:
            logger.debug('lready on')

    elif loadshedding_ends:
        logger.debug(
            f"\tWaiting {(loadshedding_ends - datetime.now()).total_seconds() / 60} more minutes before turning dryer back on")


if __name__ == "__main__":
    main()

from datetime import datetime, timedelta
from libraries import Logger

__loadshedding_ends = None


def logic(state):
    global __loadshedding_ends
    logger = Logger.Logger('f01_dryer_watchdog')

    loadshedding = state.get('loadshedding')
    grid_status = state.get('grid_status')
    dryer = state.get('dryer')

    loadshedding_status = loadshedding.get_next()
    currently_loadshedding = False
    if loadshedding_status:
        logger.debug(f"Current loadshedding status: {loadshedding_status}")
        ls_window_start = loadshedding_status['_start'] - timedelta(minutes=3)
        ls_window_end = loadshedding_status['_start'] + timedelta(minutes=60)
        currently_loadshedding = ls_window_start < datetime.now() < ls_window_end

        if currently_loadshedding and not __loadshedding_ends:
            __loadshedding_ends = ls_window_end

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

    elif (__loadshedding_ends and datetime.now() > __loadshedding_ends and grid_power) or (
            grid_power and not __loadshedding_ends):
        __loadshedding_ends = None

        if dryer.switch == 'off':
            logger.info(f'Turning {dryer} on')
            dryer.on()
        else:
            logger.debug('Already on')

    elif __loadshedding_ends:
        logger.debug(
            f"\tWaiting {(__loadshedding_ends - datetime.now()).total_seconds() / 60} more minutes before turning dryer back on")

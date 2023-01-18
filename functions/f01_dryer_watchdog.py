from datetime import datetime, timedelta
from libraries import Logger

__loadshedding_ends = None


def logic(state):
    global __loadshedding_ends
    logger = Logger.Logger('f01_dryer_watchdog')
    logger.info(f"------------------------------------------")

    loadshedding = state.get('loadshedding')
    grid_status = state.get('grid_status')
    dryer = state.get('dryer')

    loadshedding_status = loadshedding.get_next()
    logger.info(f"Next loadshedding schedule: {loadshedding_status}")
    currently_loadshedding = False
    if loadshedding_status:
        ls_window_start = loadshedding_status['_start'] - timedelta(minutes=3)
        ls_window_end = loadshedding_status['_start'] + timedelta(minutes=60)
        currently_loadshedding = ls_window_start < datetime.now() < ls_window_end

        if currently_loadshedding and not __loadshedding_ends:
            __loadshedding_ends = ls_window_end

    grid_power = True if grid_status.get_value() == 1 else False

    logger.info(f"Checking if the dryer needs to be turned off")
    logger.debug(f"\tloadshedding{currently_loadshedding:>20}")
    logger.debug(f"\tgrid_power  {grid_power:>20}")

    # If no grid or there is a loadshedding schedule now
    if not grid_power or currently_loadshedding:
        logger.debug(f"Dryer needs to be off, currently is: {dryer.switch}")

        if dryer.switch == 'on':
            logger.info(f'Turning {dryer} off')
            dryer.off()

    # Else, if there was loadshedding, and the end date for the loadshedding has passed, and there is grid
    # Or there is grid power and there was no loadshedding
    elif (__loadshedding_ends and datetime.now() > __loadshedding_ends and grid_power) or \
            (grid_power and not __loadshedding_ends):
        __loadshedding_ends = None
        logger.info(f"Turning dryer on, currently {dryer.switch}")

        if dryer.switch == 'off':
            logger.info(f'Turning {dryer} on')
            dryer.on()

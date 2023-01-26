from datetime import datetime, timedelta
from libraries import Logger
from libraries.Schedular import Task


class DryerWatchdogTask(Task):
    def __init__(self, arguments):
        self._Task__logger = None
        super().__init__(60, 'Dryer Watchdog',
                         "Estimates loadshedding, then ensures the tumble dryer device can't be activate while the power is out")
        self.__arguments = arguments
        self.__arguments['loggers']['f01_dryer_watchdog'] = self._Task__logger

        self.loadshedding_ends = None
        self.loadshedding_status = None

        self.outputs = {
            'gridStatus': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Grid Status',
                    'value': True,
                }
            }
        }

    def logic(self):
        self._Task__logger.update_file_handler()
        self._Task__logger.info(f"------------------------------------------")

        loadshedding = self.__arguments['helpers']['loadshedding']
        grid_status = self.__arguments['registers']['grid_status']
        dryer = self.__arguments['devices']['dryer']

        self.loadshedding_status = loadshedding.get_next()
        self._Task__logger.info(f"Next loadshedding schedule: {self.loadshedding_status}")
        currently_loadshedding = False
        if self.loadshedding_status:
            ls_window_start = self.loadshedding_status['_start'] - timedelta(minutes=3)
            ls_window_end = self.loadshedding_status['_start'] + timedelta(minutes=60)
            currently_loadshedding = ls_window_start < datetime.now() < ls_window_end

            if currently_loadshedding and not self.loadshedding_ends:
                self.loadshedding_ends = ls_window_end

        grid_power = True if grid_status.get_value() == 1 else False

        self._Task__logger.info(f"Checking if the dryer needs to be turned off")
        self._Task__logger.debug(f"\tloadshedding{currently_loadshedding:>20}")
        self._Task__logger.debug(f"\tgrid_power  {grid_power:>20}")

        # If no grid or there is a loadshedding schedule now
        if not grid_power or currently_loadshedding:
            self._Task__logger.debug(f"Dryer needs to be off, currently is: {dryer.switch}")

            if dryer.switch == 'on':
                self._Task__logger.info(f'Turning {dryer} off')
                dryer.off()

        # Else, if there was loadshedding, and the end date for the loadshedding has passed, and there is grid
        # Or there is grid power and there was no loadshedding
        elif (self.loadshedding_ends and datetime.now() > self.loadshedding_ends and grid_power) or \
                (grid_power and not self.loadshedding_ends):
            self.loadshedding_ends = None
            self._Task__logger.info(f"Turning dryer on, currently {dryer.switch}")

            if dryer.switch == 'off':
                self._Task__logger.info(f'Turning {dryer} on')
                dryer.on()

        self.outputs = {
            'gridStatus': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Grid Status',
                    'value': grid_status,
                }
            }
        }

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

        self.config__minutes_before = 3
        self.config__minutes_after = 60

        self.outputs = {
            'gridStatus': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Grid Status',
                    'value': True,
                }
            },
            'NextLoadshedding': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Loadshedding starts in: (hrs)',
                    'value': 0,
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
            ls_window_start = self.loadshedding_status['_start'] - timedelta(minutes=self.config__minutes_before)
            ls_window_end = self.loadshedding_status['_start'] + timedelta(minutes=self.config__minutes_after)
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


        display_value = "None"
        try:
            if self.loadshedding_status is not None:
                display_value = f"Ends in {round(self.loadshedding_status.get('end') or -1, 2)} hours"
        except Exception as e:
            display_value = "Some fucking dogshit failed for some dumbshit reason, honestly I don't know"

        self._Task__logger.info(f"Grid power, {grid_power}; Display value, {display_value}")

        self.outputs = {
            'gridStatus': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Grid Status',
                    'value': "On" if grid_power else "Off",
                }
            },
            'NextLoadshedding': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Loadshedding starts in',
                    'value': display_value,
                }
            }
        }

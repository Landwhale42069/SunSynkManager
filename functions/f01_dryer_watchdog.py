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
                    'value': "Off",
                }
            }
        }

    def logic(self):
        self._Task__logger.update_file_handler()
        self._Task__logger.info(f"------------------------------------------")

        grid_status = self.__arguments['registers']['grid_status']
        dryer = self.__arguments['devices']['dryer']

        grid_power = True if grid_status.get_value() == 1 else False

        self._Task__logger.info(f"Checking if the dryer needs to be turned off")
        self._Task__logger.debug(f"\tgrid_power  {grid_power:>20}")

        # If no grid
        if not grid_power:
            self._Task__logger.debug(f"Dryer needs to be off, currently is: {dryer.switch}")

            if dryer.switch == 'on':
                self._Task__logger.info(f'Turning {dryer} off')
                dryer.off()

        # Else, if there was loadshedding, and the end date for the loadshedding has passed, and there is grid
        # Or there is grid power and there was no loadshedding
        else:
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
                    'value': "On" if grid_power else "Off",
                }
            }
        }

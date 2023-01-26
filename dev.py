from functions.f02_battery_saver import BatterySaverTask
from functions.f01_dryer_watchdog import DryerWatchdogTask

config = {
    "loggers": {}
}

a = BatterySaverTask(config)
b = DryerWatchdogTask(config)

print()


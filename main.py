from libraries import Logger, eWeLink, Inverter, Loadshedding, Interface, Schedular
from functions import f01_dryer_watchdog, f02_battery_saver

from datetime import datetime


def main():

    # Create and set static logger for Device and Register
    eWeLink.Device.logger = Logger.Logger('eWeLink')
    Inverter.Register.logger = Logger.Logger('Inverter')
    Loadshedding.Tracker.logger = Logger.Logger('Loadshedding')
    Interface.WebAPI.logger = Logger.Logger('Interface')

    loadshedding = Loadshedding.Tracker("schedule.csv")

    # Define devices
    dryer = eWeLink.Device('100168b564')
    geyser1 = eWeLink.Device('10017e9016')
    geyser1.expected_usage = 2000
    geyser1.expected_activity = [
        {
            'start': datetime.strptime('14:30', '%H:%M').time(),
            'end': datetime.strptime('16:30', '%H:%M').time(),
        },
        {
            'start': datetime.strptime('8:30', '%H:%M').time(),
            'end': datetime.strptime('10:30', '%H:%M').time(),
        },
    ]

    geyser2 = eWeLink.Device('100178de05')
    geyser2.expected_usage = 2000

    pool_pump = eWeLink.Device('1001793ec2')
    pool_pump.expected_usage = 2000
    pool_pump.expected_activity = [
        {
            'start': datetime.strptime('14:30', '%H:%M').time(),
            'end': datetime.strptime('16:30', '%H:%M').time(),
        },
        {
            'start': datetime.strptime('8:30', '%H:%M').time(),
            'end': datetime.strptime('10:30', '%H:%M').time(),
        },
    ]

    stoep = eWeLink.Device('10012b9022')
    marco_kamer = eWeLink.Device('1000f6e808')

    # Define registers
    battery_soc = Inverter.Register(184, "Battery SOC", -1, "%")
    battery_power = Inverter.Register(190, "Battery power", -1, "Watt")
    grid_power = Inverter.Register(169, "Grid power", -1, "Watt")
    load_power = Inverter.Register(178, "Load power", -1, "Watt")
    pv1_power = Inverter.Register(186, "PV1 power", -1, "Watt")
    pv2_power = Inverter.Register(187, "PV2 power", -1, "Watt")
    grid_status = Inverter.Register(194, "Grid Connected Status")

    argument_dict = {
        'loadshedding': loadshedding,

        'dryer': dryer,
        'geyser1': geyser1,
        'geyser2': geyser2,
        'pool_pump': pool_pump,
        'stoep': stoep,
        'marco_kamer': marco_kamer,

        'battery_soc': battery_soc,
        'battery_power': battery_power,
        'grid_power': grid_power,
        'load_power': load_power,
        'pv1_power': pv1_power,
        'pv2_power': pv2_power,
        'grid_status': grid_status,
    }

    f02_battery_saver.logic(argument_dict)
    print()

    web_interface = Interface.WebAPI("interface", argument_dict)
    web_interface.startup()

    t01_dryer_watchdog = Schedular.IntervalTask(60, f01_dryer_watchdog.logic, [argument_dict])
    t01_dryer_watchdog.start()


if __name__ == "__main__":
    main()

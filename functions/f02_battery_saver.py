from datetime import datetime, timedelta
from libraries.Schedular import Task


class BatterySaverTask(Task):
    def __init__(self, arguments):
        self._Task__logger = None
        super().__init__(10, 'Battery Saver',
                         "Uses the charge rate of the inverter battery to estimate the future state of the battery, then disables controllable devices to correct")
        self.__arguments = arguments
        self.__arguments['loggers']['f02_battery_saver'] = self._Task__logger

        self.config__battery_Wh_capacity = 10800
        self.config__projected_duration = 2
        self.config__ideal_value = 40
        self.config__factor = 1

        self.__sample_buffer_size = 10
        self.__sample_buffer = [0] * self.__sample_buffer_size
        self.__sample_taken_dates = [datetime.now().strftime('%H:%M:%S')] * self.__sample_buffer_size
        self.additional_attributes = [
            'config__sample_buffer_size'
        ]

        self.outputs = {
            'currentBattery': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Current battery',
                    'value': 100,
                }
            },
            'solarPredictionMax': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Prediction (Max)',
                    'value': 0,
                }
            },
            'solarPredictionMoving': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Prediction (Moving)',
                    'value': 0,
                }
            },
            'averageUsage': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Average usage (W)',
                    'value': 0,
                }
            },
            'expectedBattery': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Expected battery (%)',
                    'value': 0,
                }
            },
            'shedAmount': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Will try to drop (w)',
                    'value': 0,
                }
            },
            'geyserKitchenManagement': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Kitchen Geyser',
                    'value': 0,
                }
            },
            'geyserBathroomManagement': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Bathroom Geyser',
                    'value': 0,
                }
            },
            'poolpumpManagement': {
                'type': 'SimpleDisplay',
                'content': {
                    'title': 'Pool Pump',
                    'value': 0,
                }
            },
            'sampleBuffer': {
                'type': 'Chart',
                'name': 'Sample Buffer',
                'content': {
                    'title': {
                        'text': "Sample Buffer",
                        'align': 'centre',
                    },
                    'chart': {
                        'type': 'line',
                        'toolbar': {
                            'show': False,
                        },
                        'animations': {
                            'enabled': False,
                        }
                    },
                    'series': [{
                        'name': 'Battery Power',
                        'data': self.__sample_buffer
                    }],
                    'xaxis': {
                        'categories': self.__sample_taken_dates
                    },
                    'yaxis': {
                        'min': -5000,
                        'max': 5000,
                    }
                }
            },
            'solarPredictorMax': {
                'type': 'Chart',
                'name': 'Max Predictor',
                'content': {
                    'title': {
                        'text': "Max Predictor",
                        'align': 'centre',
                    },
                    'chart': {
                        'type': 'line',
                        'toolbar': {
                            'show': False,
                        },
                        'animations': {
                            'enabled': False,
                        }
                    },
                    'series': [{
                        'name': 'Battery Power',
                        'data': [55]
                    }],
                    'xaxis': {
                        'categories': [10]
                    },
                    'yaxis': {
                        'min': 0,
                        'max': 10000,
                    }
                }
            },
            'solarPredictorMoving': {
                'type': 'Chart',
                'name': 'Moving Predictor',
                'content': {
                    'title': {
                        'text': "Moving Predictor",
                        'align': 'centre',
                    },
                    'chart': {
                        'type': 'line',
                        'toolbar': {
                            'show': False,
                        },
                        'animations': {
                            'enabled': False,
                        }
                    },
                    'series': [{
                        'name': 'Battery Power',
                        'data': self.__sample_buffer
                    }],
                    'xaxis': {
                        'categories': self.__sample_taken_dates
                    },
                    'yaxis': {
                        'min': 0,
                        'max': 10000,
                    }
                }
            },
        }

        self.disabled_devices = []

    @property
    def sample_buffer_size(self):
        return self.__sample_buffer_size

    @sample_buffer_size.setter
    def sample_buffer_size(self, new_sample_buffer_size):
        if new_sample_buffer_size <= 0:
            return

        difference = self.sample_buffer_size - new_sample_buffer_size
        if difference > 0:
            self.__sample_buffer = self.__sample_buffer[difference::]
            self.__sample_taken_dates = self.__sample_taken_dates[difference::]
        elif difference < 0:
            self.__sample_buffer = [0] * abs(difference) + self.__sample_buffer
            self.__sample_taken_dates = [datetime.now().strftime('%H:%M:%S')] * abs(difference) + self.__sample_taken_dates

        self.__sample_buffer_size = new_sample_buffer_size

    def logic(self):
        self._Task__logger.update_file_handler()
        battery_soc = self.__arguments['registers']['battery_soc']
        battery_power = self.__arguments['registers']['battery_power']

        solar_predictor = self.__arguments['helpers']['solar_predictor']

        geyser_kitchen = self.__arguments['devices']['geyser_kitchen']
        geyser_bathroom = self.__arguments['devices']['geyser_bathroom']
        pool_pump = self.__arguments['devices']['pool_pump']

        # Buffer battery power history
        self.__sample_buffer.append(battery_power.get_value())
        self.__sample_buffer.pop(0)
        self.__sample_taken_dates.append(datetime.now().strftime('%H:%M:%S'))
        self.__sample_taken_dates.pop(0)

        current_percent = battery_soc.get_value()
        average_battery_power = sum(self.__sample_buffer) / len(self.__sample_buffer)
        power_left = (current_percent / 100) * self.config__battery_Wh_capacity

        expected_percentage_left = ((power_left - average_battery_power * self.config__projected_duration) / self.config__battery_Wh_capacity) * 100

        self._Task__logger.debug(f"\tCurrent       | {round(current_percent, 2):>20} %")
        self._Task__logger.debug(f"\tAverage usage | {round(average_battery_power, 2):>20}")
        self._Task__logger.debug(f"\tExpected left | {round(expected_percentage_left, 2):>20} %")

        missing_percentage = self.config__ideal_value - expected_percentage_left
        # Power to drop = missing power (Wh) * time to recover (1/h) * ratio
        power_to_drop = (missing_percentage / 100) * self.config__battery_Wh_capacity * (
                    1 / self.config__projected_duration) * self.config__factor

        self._Task__logger.info(f"Going to try to drop {round(power_to_drop, 2)} W")

        if power_to_drop > 0:
            _device = geyser_kitchen
            _usage = _device.get_usage()
            if power_to_drop > _usage and _device.lock is None:
                self._Task__logger.debug(f"{_device.name} is using {_usage} W, turning off")
                power_to_drop -= _usage
                _device.shutdown()
                _device.lock = "f02"

            _device = geyser_bathroom
            _usage = _device.get_usage()
            if power_to_drop > _usage and _device.lock is None:
                self._Task__logger.debug(f"{_device.name} is using {_usage} W, turning off")
                power_to_drop -= _usage
                _device.shutdown()
                _device.lock = "f02"

            _device = pool_pump
            _usage = _device.get_usage()
            if power_to_drop > _usage and _device.lock is None:
                self._Task__logger.debug(f"{_device.name} is using {_usage} W, turning off")
                power_to_drop -= _usage
                _device.shutdown()
                _device.lock = "f02"

        else:
            _device = geyser_kitchen
            _usage = _device.get_usage(if_on=True)
            if -power_to_drop > _usage and _device.lock == "f02":
                self._Task__logger.debug(f"{_device.name} will use {_usage} W, turning on")
                power_to_drop += _usage
                _device.startup()
                _device.lock = None

            try:

                _device = geyser_bathroom
                _usage = _device.get_usage(if_on=True)
                _temp = float(_device.obj.get('params').get("currentTemperature"))
                if -power_to_drop > _usage and _temp < 44.5 and _device.lock == "f02":
                    self._Task__logger.debug(f"{_device.name} will use {_usage} W, turning on")
                    power_to_drop += _usage
                    _device.startup()
                    _device.lock = None
            except Exception as e:
                self._Task__logger.warning(f"Error when trying to turn {geyser_bathroom.name} back on, {e}")

            _device = pool_pump
            _usage = _device.get_usage(if_on=True)
            _start = datetime.now().replace(hour=8, minute=30, second=0, microsecond=0)
            _end = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
            if -power_to_drop > _usage and _start < datetime.now() < _end and _device.lock == "f02":
                self._Task__logger.debug(f"{_device.name} will use {_usage} W, turning on")
                power_to_drop += _usage
                _device.startup()
                _device.lock = None

        self.outputs['solarPredictionMax']['content']['value'] = f"{round(solar_predictor.get(datetime.now() + timedelta(hours=self.config__projected_duration), method='max'), 2)} W"
        self.outputs['solarPredictionMoving']['content']['value'] = f"{round(solar_predictor.get(datetime.now() + timedelta(hours=self.config__projected_duration)), 2)} W"

        self.outputs['currentBattery']['content']['value'] = f"{round(current_percent, 2)} %"
        self.outputs['averageUsage']['content']['value'] = f"{round(average_battery_power, 2)} W"
        self.outputs['expectedBattery']['content']['value'] = f"{round(expected_percentage_left, 2)} %"
        self.outputs['shedAmount']['content']['value'] = f"{round(power_to_drop, 2)} W"

        try:
            self.outputs['geyserKitchenManagement']['content']['value'] = f"Normal" if geyser_kitchen.lock is None else f"Disabled"
            self.outputs['geyserBathroomManagement']['content']['value'] = f"Normal" if geyser_bathroom.lock is None else f"Disabled"
            self.outputs['poolpumpManagement']['content']['value'] = f"Normal" if pool_pump.lock is None else f"Disabled"
        except Exception as e:
            self._Task__logger.error("Error trying to set outputs for devices")

        self.outputs['sampleBuffer']['content']['series'][0] = {
            'name': 'Battery Power',
            'data': self.__sample_buffer
        }
        self.outputs['sampleBuffer']['content']['xaxis']['categories'] = self.__sample_taken_dates

        # MAX
        max_data = solar_predictor.MaxModel.get_model()
        self.outputs['solarPredictorMax']['content']['series'][0] = {
            'name': 'Max Solar',
            'data': max_data['y']
        }
        self.outputs['solarPredictorMax']['content']['xaxis']['categories'] = [x/3600 for x in max_data['x']]

        # MOVING
        moving_data = solar_predictor.MovingModel[-1].get_model()
        self.outputs['solarPredictorMoving']['content']['series'][0] = {
            'name': 'Moving Solar',
            'data': moving_data['y']
        }
        self.outputs['solarPredictorMoving']['content']['xaxis']['categories'] = [x/3600 for x in moving_data['x']]

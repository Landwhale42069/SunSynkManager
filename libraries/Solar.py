from datetime import datetime
import os
import json
from threading import Timer


class Predictor:
    logger = None
    battery_register = None
    pv_registers = []

    def __init__(self):
        self.MaxModel = None
        self.BaseModel = None
        self.LatestMovingModel = None
        self.MovingModel = []
        if os.path.exists('data/Predictor.json'):
            self.logger.info(f"Data file available, importing...")
            with open('data/Predictor.json', 'r') as f:
                data_import = json.load(f)
                self.logger.debug(f"\tData: {data_import}")
                self.BaseModel = Model().from_json(data_import['BaseModel'])
                self.MaxModel = Model().from_json(data_import['MaxModel'])
                self.MovingModel = [Model().from_json(_data) for _data in data_import['MovingModel']]
                self.LatestMovingModel = Model().from_json(data_import['LatestMovingModel'])
        else:
            self.logger.info(f"Creating startup model")
            self.BaseModel = Model()
            self.BaseModel.add_sample(17, datetime(2023, 1, 1, 0))
            self.BaseModel.add_sample(14, datetime(2023, 1, 1, 1))
            self.BaseModel.add_sample(21, datetime(2023, 1, 1, 2))
            self.BaseModel.add_sample(22, datetime(2023, 1, 1, 3))
            self.BaseModel.add_sample(121, datetime(2023, 1, 1, 4))
            self.BaseModel.add_sample(763, datetime(2023, 1, 1, 5))
            self.BaseModel.add_sample(3816, datetime(2023, 1, 1, 6))
            self.BaseModel.add_sample(6417, datetime(2023, 1, 1, 7))
            self.BaseModel.add_sample(7913, datetime(2023, 1, 1, 8))
            self.BaseModel.add_sample(8300, datetime(2023, 1, 1, 9))
            self.BaseModel.add_sample(8500, datetime(2023, 1, 1, 10))
            self.BaseModel.add_sample(8400, datetime(2023, 1, 1, 11))
            self.BaseModel.add_sample(8202, datetime(2023, 1, 1, 12))
            self.BaseModel.add_sample(7652, datetime(2023, 1, 1, 13))
            self.BaseModel.add_sample(6952, datetime(2023, 1, 1, 14))
            self.BaseModel.add_sample(5534, datetime(2023, 1, 1, 15))
            self.BaseModel.add_sample(3796, datetime(2023, 1, 1, 16))
            self.BaseModel.add_sample(1536, datetime(2023, 1, 1, 17))
            self.BaseModel.add_sample(700, datetime(2023, 1, 1, 18))
            self.BaseModel.add_sample(122, datetime(2023, 1, 1, 19))
            self.BaseModel.add_sample(25, datetime(2023, 1, 1, 20))
            self.BaseModel.add_sample(8, datetime(2023, 1, 1, 21))
            self.BaseModel.add_sample(13, datetime(2023, 1, 1, 22))
            self.BaseModel.add_sample(22, datetime(2023, 1, 1, 23))

            self.LatestMovingModel = Model()
            self.MovingModel = []
            for i in range(14):
                self.MovingModel.append(Model().copy(self.BaseModel))

            self.MaxModel = Model().copy(self.BaseModel)

        self.run = True
        self.sample_loop()

    def sample_loop(self):
        self.logger.info('Sampling loop')
        if self.run:
            Timer(300, self.sample_loop, []).start()

        try:
            if self.battery_register.get_value() < 98:
                total_pv = sum([pv_register.get_value() for pv_register in self.pv_registers])
                self.record_sample(total_pv)
        except Exception as e:
            self.run = False

    def record_sample(self, value):
        self.logger.info(f'Recording {value} W into models')
        if 0 < datetime.now().time().hour < 1 and len(self.LatestMovingModel.samples) > 60:
            self.logger.debug(f'Time to restart LatestMovingModel')
            self.MovingModel.append(self.LatestMovingModel)
            self.MovingModel.pop(0)
            self.LatestMovingModel = Model()
            self.LatestMovingModel.add_sample(value, datetime.now())
        else:
            self.logger.debug(f'Adding sample to LatestMovingModel')
            self.LatestMovingModel.add_sample(value, datetime.now())

        last_max_value = self.MaxModel.get_power(datetime.now())
        if value > last_max_value:
            self.logger.debug(f'Last Max value: {last_max_value} is smaller than this sample: {value}, inserting')
            self.MaxModel.replace_sample(value, datetime.now())

        with open('data/Predictor.json', 'w+') as f:
            self.logger.debug(f'Exporting to file')
            data_export = {
                'BaseModel': self.BaseModel.to_json(),
                'MaxModel': self.MaxModel.to_json(),
                'MovingModel': [model.to_json() for model in self.MovingModel],
                'LatestMovingModel': self.LatestMovingModel.to_json(),
            }
            json.dump(data_export, f)

    def get(self, date, method='moving'):
        if method == 'moving':
            moving_powers = [model.get_power(date) for model in self.MovingModel]
            return (sum(moving_powers) + self.LatestMovingModel.get_power(date))/(len(self.MovingModel) + 1)
        elif method == 'max':
            return self.MaxModel.get_power(date)
        else:
            return 0


class Model:
    def __init__(self):
        self.samples = []

    def copy(self, other_model):
        self.samples = [s for s in other_model.samples]
        return self

    def to_json(self):
        return [{
            'value': s['value'],
            'date': s['date'].isoformat(),
        } for s in self.samples]

    def from_json(self, input_samples):
        self.samples = [{
            'value': s['value'],
            'date': datetime.fromisoformat(s['date']),
        } for s in input_samples]
        return self

    def add_sample(self, sample, date=datetime.now()):
        self.samples.append({
            'value': sample,
            'date': date,
        })
        self.samples = sorted(self.samples, key=lambda d: (3600*d['date'].hour + d['date'].minute + d['date'].second))

    def replace_sample(self, sample, date=datetime.now()):
        if len(self.samples) == 0:
            return

        nearest = (None, 9999999999)
        for _sample in self.samples:
            current_date_sample = datetime(date.year, date.month, date.day, _sample['date'].hour, _sample['date'].minute, _sample['date'].second)
            difference = abs((current_date_sample - date).total_seconds())
            if nearest[0] is None or difference < nearest[1]:
                nearest = (_sample, difference)

        self.samples.pop(self.samples.index(nearest[0]))
        self.add_sample(sample, date)

    def get_model(self):
        return {
            'y': [s['value'] for s in self.samples],
            'x': [3600*s['date'].hour + 60*s['date'].minute + 60*s['date'].second for s in self.samples],
        }

    def get_nearest(self, date):
        if len(self.samples) == 0:
            return 0

        nearest = (None, 9999999999)
        for _sample in self.samples:
            current_date_sample = datetime(date.year, date.month, date.day, _sample['date'].hour, _sample['date'].minute, _sample['date'].second)
            difference = abs((current_date_sample - date).total_seconds())
            if nearest[0] is None or difference < nearest[1]:
                nearest = (_sample, difference)

        return nearest[0]['value']

    def get_power(self, date):
        if len(self.samples) < 2:
            return self.get_nearest(date)

        for index in range(len(self.samples)-1):
            start, end = self.samples[index], self.samples[index+1]
            if start['date'].time() < date.time() < end['date'].time():
                _start = 3600*start['date'].hour + 60*start['date'].minute + start['date'].second
                _end = 3600*end['date'].hour + 60*end['date'].minute + end['date'].second
                _now = 3600*date.hour + 60*date.minute + date.second

                ratio = (_now - _start) / (_end - _start)

                return start['value']*ratio + end['value']*(1-ratio)

        return self.get_nearest(date)




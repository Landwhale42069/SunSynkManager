from libraries import Solar, Logger
from datetime import datetime

Solar.Predictor.logger = Logger.Logger('SunPredictor')
a = Solar.Predictor()

a.record_sample(22)
...

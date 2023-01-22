from libraries import Logger, eWeLink

eWeLink.DeviceManager.logger = Logger.Logger('eWeLink')

DeviceManager = eWeLink.DeviceManager()

stoep = DeviceManager.get_device('10012b9022')
geyser_kitchen = DeviceManager.get_device('10017e9016')
geyser_bathroom = DeviceManager.get_device('100178de05')
pool_pump = DeviceManager.get_device('1001793ec2')
marco_kamer = DeviceManager.get_device('1000f6e808')

print()


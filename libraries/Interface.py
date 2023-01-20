from flask import Flask, send_file, request
from flask_cors import CORS
import logging
import threading
import os

import libraries.Inverter


class WebAPI:
    logger = None

    def __init__(self, interface_directory, info):
        self.interface_directory = interface_directory
        self.info = info

        self.app = Flask(__name__)
        # Disable logging
        log = logging.getLogger('werkzeug')
        log.disabled = True

        self.cors = CORS(self.app, resources={r"/*": {"origins": "*"}})

        # Host index.html
        @self.app.route("/")
        def base_html():
            self.logger.debug('Getting index.html')
            _file = os.path.join(os.getcwd(), interface_directory, 'index.html')
            return send_file(_file)

        # Host interface files
        @self.app.route("/<location>")
        def alt_html(location):
            self.logger.debug(f'Getting {location}')
            if location in ['manager', 'viewer']:
                return base_html()
            else:
                _file = os.path.join(os.getcwd(), interface_directory, location)
                return send_file(_file)

        # Host device data
        @self.app.route("/api/devices")
        def devices():
            self.logger.debug('Getting devices')

            return_dict = [
                self.info.get('dryer'),
                self.info.get('geyser1'),
                self.info.get('geyser2'),
                self.info.get('pool_pump'),
                self.info.get('stoep'),
                self.info.get('marco_kamer'),
            ]

            [_device.refresh(5) for _device in return_dict]

            return [_device.obj for _device in return_dict]

        # Host device data
        @self.app.route("/api/switchDevice", methods=['POST'])
        def switch_device():
            device_id = request.args.get('deviceId')
            outlet = request.args.get('outlet')
            if outlet is None:
                outlet = -1
            else:
                outlet = int(outlet)

            _error = 'Specify deviceId'
            if device_id is not None and device_id != 'undefined':
                self.logger.debug(f'Toggling device with device_id{device_id}')
                try:
                    for _property in self.info:
                        device = self.info[_property]
                        if hasattr(device, 'device_id'):
                            if device.device_id == device_id:
                                device.toggle(outlet)
                                break

                    return {
                        'success': True
                    }
                except Exception as e:
                    _error = e

            return {
                'error': _error
            }

        # Host inverter data
        @self.app.route("/api/inverter")
        def inverter():
            self.logger.debug('Getting inverter')

            return_dict = [
                self.info.get('battery_soc'),
                self.info.get('battery_power'),
                self.info.get('grid_power'),
                self.info.get('load_power'),
                self.info.get('pv1_power'),
                self.info.get('pv2_power'),
                self.info.get('grid_status'),
            ]

            return_dict = [{
                "name": _register.name,
                "value": _register.get_value(),
                "units": _register.units,
            } for _register in return_dict]

            return_dict.insert(6, {
                "name": "Total PV power",
                "value": return_dict[4]['value'] + return_dict[5]['value'],
                "units": "W",
            })

            return return_dict

        # Host track data
        @self.app.route("/api/tasks")
        def tasks():
            self.logger.debug('Getting tasks')

            return_dict = [
                self.info.get('t01_dryer_watchdog'),
                self.info.get('t02_battery_saver')
            ]

            return [
                {
                    'name': task.name,
                    'active': task.active,
                    'logs': task.logs,
                } for task in return_dict
            ]

    def startup(self):
        x = threading.Thread(target=self.app.run, kwargs={
            'host': "0.0.0.0"
        })
        x.start()


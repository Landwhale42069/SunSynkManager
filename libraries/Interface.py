from flask import Flask, send_file, request
from flask_cors import CORS
import logging
import threading
import os


class WebAPI:
    logger = None

    def __init__(self, interface_directory, info):
        self.interface_directory = interface_directory
        self.info = info

        self.app = Flask(__name__)
        # Disable logging
        # log = logging.getLogger('werkzeug')
        # log.disabled = True

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
                self.info.get('dryer').obj,
                self.info.get('geyser1').obj,
                self.info.get('geyser2').obj,
                self.info.get('pool_pump').obj,
                self.info.get('stoep').obj,
            ]

            return return_dict

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

    def startup(self):
        x = threading.Thread(target=self.app.run, kwargs={
            'host': "0.0.0.0"
        })
        x.start()


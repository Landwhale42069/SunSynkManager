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
            if location in ['administrator', 'basic']:
                return base_html()
            else:
                _file = os.path.join(os.getcwd(), interface_directory, location)
                return send_file(_file)

        # Host device data
        @self.app.route("/api/devices")
        def devices():
            _devices = self.info.get('devices')
            return_dict = [
                _devices.get('dryer'),
                _devices.get('geyser_kitchen'),
                _devices.get('geyser_bathroom'),
                _devices.get('pool_pump'),
            ]

            [_device.refresh() for _device in return_dict]

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
                self.logger.debug(f'Toggling device with device_id {device_id}')
                try:
                    for _property in self.info['devices']:
                        device = self.info['devices'][_property]
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
            _registers = self.info['registers']
            return_dict = [
                _registers.get('battery_soc'),
                _registers.get('battery_power'),
                _registers.get('grid_power'),
                _registers.get('load_power'),
                _registers.get('pv1_power'),
                _registers.get('pv2_power'),
                _registers.get('grid_status'),
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

            task_list = self.info['tasks']

            return_dict = [{
                "name": self.info["tasks"][task].name,
                "description": self.info["tasks"][task].description,
                "taskId": self.info["tasks"][task].task_id,
            } for task in task_list]

            return return_dict

        @self.app.route("/api/task/config")
        def get_task_config():
            task_id = request.args.get('taskId')
            if task_id is None:
                return {
                    'error': 'taskId is required'
                }
            self.logger.debug(f'Getting Task {task_id}\'s config')

            task = [self.info['tasks'][_task] for _task in self.info['tasks'] if self.info['tasks'][_task].task_id == int(task_id)]

            if len(task) != 1:
                return {
                    'error': f'Expected 1 task with the taskId {task_id}, instead got {len(task)}'
                }

            return task[0].get_config()

        @self.app.route("/api/task/config", methods=['POST'])
        def set_task_config():
            task_id = request.args.get('taskId')
            body = request.json

            if task_id is None:
                return {
                    'error': 'taskId is required'
                }
            self.logger.debug(f'Getting Task {task_id}\'s config')

            task = [self.info['tasks'][_task] for _task in self.info['tasks'] if self.info['tasks'][_task].task_id == int(task_id)]

            if len(task) != 1:
                return {
                    'error': f'Expected 1 task with the taskId {task_id}, instead got {len(task)}'
                }

            task[0].set_config(body)

            return {
                'success': True,
            }

        # Host track data
        @self.app.route("/api/logs")
        def logs():
            self.logger.debug('Getting logs')

            loggers = self.info.get('loggers')

            return_dict = [{
                    'name': _logger,
                    'logs': self.get_logs(loggers.get(_logger).directory, _logger),
                } for _logger in loggers]

            return return_dict

    def startup(self):
        x = threading.Thread(target=self.app.run, kwargs={
            'host': "0.0.0.0"
        })
        x.start()

    @staticmethod
    def get_logs(directory, name):
        log_content = []
        for file in os.listdir(directory):
            if name in file:
                with open(os.path.join(directory, file)) as log_file:
                    log_content.append({
                        "name": file,
                        "content": log_file.read()
                    })

        return log_content


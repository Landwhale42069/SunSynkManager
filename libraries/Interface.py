from flask import Flask, send_file
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

        self.cors = CORS(self.app, resources={r"/devices": {"origins": "*"}})

        # Host index.html
        @self.app.route("/")
        def base_html():
            self.logger.debug('Getting index.html')
            _file = os.path.join(os.getcwd(), interface_directory, 'index.html')
            return send_file(_file)

        # Host index.html
        @self.app.route("/<location>")
        def alt_html(location):
            self.logger.debug(f'Getting {location}')
            _file = os.path.join(os.getcwd(), interface_directory, location)
            return send_file(_file)

        # Host device data
        @self.app.route("/devices")
        def devices():
            self.logger.debug('Getting devices')
            return_dict = [
                self.info.get('dryer').obj,
                self.info.get('geyser1').obj,
                self.info.get('geyser2').obj,
                self.info.get('pool_pump').obj,
            ]

            return return_dict

    def startup(self):
        x = threading.Thread(target=self.app.run, kwargs={
            'host': "0.0.0.0"
        })
        x.start()


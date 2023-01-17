from flask import Flask, send_file
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
        log = logging.getLogger('werkzeug')
        log.disabled = True

        # Host index.html
        @self.app.route("/")
        def html():
            self.logger.debug('Getting index.html')
            index_html = os.path.join(os.getcwd(), interface_directory, 'index.html')
            return send_file(index_html)

        # Host style.css
        @self.app.route("/main.7f1ac37130d7c240.js")
        def main():
            self.logger.debug('Getting main.js')
            _file = os.path.join(os.getcwd(), interface_directory, 'main.7f1ac37130d7c240.js')
            return send_file(_file)

        # Host main.js
        @self.app.route("/polyfills.2f9d9899c1a6ea1b.js")
        def polyfills():
            self.logger.debug('Getting polyfills.js')
            _file = os.path.join(os.getcwd(), interface_directory, 'polyfills.2f9d9899c1a6ea1b.js')
            return send_file(_file)

        # Host main.js
        @self.app.route("/runtime.c64d89f55c5c6811.js")
        def runtime():
            self.logger.debug('Getting runtime.js')
            _file = os.path.join(os.getcwd(), interface_directory, 'runtime.c64d89f55c5c6811.js')
            return send_file(_file)

        # Host main.js
        @self.app.route("/styles.23fa036e24aed2f0.css")
        def styles():
            self.logger.debug('Getting styles.css')
            _file = os.path.join(os.getcwd(), interface_directory, 'styles.23fa036e24aed2f0.css')
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


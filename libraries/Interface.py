from flask import Flask, send_file
import logging
import threading
import os


class WebAPI:
    logger = None

    def __init__(self, interface_directory):
        self.interface_directory = interface_directory

        self.app = Flask(__name__)
        # Disable logging
        log = logging.getLogger('werkzeug')
        log.disabled = True

        # Host index.html
        @self.app.route("/")
        def interface_html():
            self.logger.debug('Getting index.html')
            index_html = os.path.join(os.getcwd(), interface_directory, 'index.html')
            return send_file(index_html)

        # Host style.css
        @self.app.route("/style/style.css")
        def interface_style():
            self.logger.debug('Getting style/style.css')
            style_css = os.path.join(os.getcwd(), interface_directory, 'style/style.css')
            return send_file(style_css)

        # Host main.js
        @self.app.route("/main.js")
        def interface_javascript():
            self.logger.debug('Getting main.js')
            main_js = os.path.join(os.getcwd(), interface_directory, 'main.js')
            return send_file(main_js)

    def startup(self):
        x = threading.Thread(target=self.app.run, kwargs={
            'host': "0.0.0.0"
        })
        x.start()


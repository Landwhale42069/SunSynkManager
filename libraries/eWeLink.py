import time
import random
import hmac
import json
import hashlib
import base64
import requests
from datetime import datetime
from threading import Timer

APP_ID = 'YzfeftUVcZ6twZw1OoVKPRFYTrGEg01Q'
APP_SECRET = '4G91qSoboqYO4Y0XJ0LPPKIsq8reHdfa'


class DeviceManager:
    logger = None

    def __init__(self):
        self.headers = None
        self.bearer_token = None
        self.user_apikey = None

        self.email = None
        self.password = None
        self.dev_mode = False

        self.devices = {}
        self.refresh_list = {}

        try:
            with open('credentials.csv', 'r') as f:
                credentials = f.readline()
                self.email, self.password = credentials.split(',')
                self.login(self.email, self.password)
        except FileNotFoundError as e:
            print('eWeLink-DEV')
            self.dev_mode = True

        self.populate()

        self.run = True
        self.refresh_loop()

    def login(self, email=None, password=None):
        self.logger.debug("Logging into eWeLink")
        if email is None and password is None:
            return

        body = {
            "appid": APP_ID,
            "email": email,
            "password": password,
            "ts": time.time(),
            "version": 8,
            "nonce": self.generate_nonce(15)
        }

        decrypted_app_secret = b'4G91qSoboqYO4Y0XJ0LPPKIsq8reHdfa'
        hex_dig = hmac.new(
            decrypted_app_secret,
            str.encode(json.dumps(body)),
            digestmod=hashlib.sha256).digest()

        sign = base64.b64encode(hex_dig).decode()

        self.headers = {
            'Authorization': 'Sign ' + sign,
            'Content-Type': 'application/json;charset=UTF-8'
        }

        self.logger.debug(f"Getting bearer token...")
        request = requests.post('https://eu-api.coolkit.cc:8080/api/user/login',
                                headers=self.headers, json=body)

        response = request.json()
        if 'error' in response:
            raise Exception(f"Could not log into eWeLink: ({request.status_code}) {response}")

        self.bearer_token = response['at']
        self.user_apikey = response['user']['apikey']
        self.headers.update({'Authorization': 'Bearer ' + self.bearer_token})

    @staticmethod
    def generate_nonce(length=8):
        """Generate pseudorandom number."""
        return ''.join([str(random.randint(0, 9)) for i in range(length)])

    def get_devices(self):
        if self.dev_mode:
            return [
                {
                    'name': f'Dev Device {i+1}',
                    'params': {
                        'switch': 'off',
                        'switches': [
                            {
                                'switch': 'off',
                                'outlet': 0
                            }
                        ],
                        'power': 2153
                    },
                    'deviceid': device_id,
                } for i, device_id in enumerate(['100168b564', '10017e9016', '100178de05', '1001793ec2'])]

        params = {
            "lang": 'en',
            "appid": APP_ID,
            "ts": time.time(),
            "version": 8,
            "getTags": 1,
        }
        url_params = "&".join(["{}={}".format(param, params.get(param)) for param in params])
        request = requests.get(f'https://eu-api.coolkit.cc:8080/api/user/device?{url_params}',
                               headers=self.headers)

        response = request.json()

        return response.get('devicelist')

    def populate(self):
        devices = self.get_devices()
        for device_obj in devices:
            self.devices[device_obj.get('deviceid')] = device_obj

    def refresh_loop(self):
        if self.run:
            t = Timer(10, self.refresh_loop, []).start()

        try:
            if self.run:
                self.hard_refresh()
        except Exception as e:
            self.logger.error(f"The refresh loop failed, {e}")
            self.run = False
            time.sleep(10)

            # Log back in
            self.login()
            self.run = True
            self.refresh_loop()

    def hard_refresh(self):
        if self.dev_mode:
            return

        for device in self.refresh_list.keys():
            self.hard_reload_device(device)

    def refresh(self):
        if self.dev_mode:
            return

        for device in self.refresh_list.keys():
            params = self.get_params(device)

            for param in params.keys():
                self.devices[device]['params'][param] = params[param]
                self.refresh_list[device]['params'][param] = params[param]

    def get_params(self, device_id):
        if self.dev_mode:
            return

        params = {
            "deviceid": device_id,
            "lang": 'en',
            "appid": APP_ID,
            "ts": time.time(),
            "version": 8,
            "getTags": 1,
            "params": 'switch|switches|power',
        }
        url_params = "&".join(["{}={}".format(param, params.get(param)) for param in params])
        request = requests.get(f'https://eu-api.coolkit.cc:8080/api/user/device/status?{url_params}',
                               headers=self.headers)

        response = request.json()

        if 'error' in response and response['error'] != 0:
            raise Exception(response)

        return response.get('params')

    def get_device(self, device_id):
        _obj = self.devices.get(device_id)
        self.refresh_list[device_id] = _obj

        return Device(device_id, self, self.logger)

    def hard_reload_device(self, device_id):
        if self.dev_mode:
            return
        params = {
            "deviceid": device_id,
            "appid": APP_ID,
            "version": 8,
            "ts": time.time(),
        }
        url_params = "&".join(["{}={}".format(param, params.get(param)) for param in params])
        request = requests.get(f'https://eu-api.coolkit.cc:8080/api/user/device/{device_id}?{url_params}',
                               headers=self.headers)

        try:
            response = request.json()
        except Exception as e:
            raise Exception(e)

        if 'error' in response and response.get('error') != 0:
            raise Exception(f"Error while getting device {device_id}, {response}")

        self.devices[device_id] = response
        self.refresh_list[device_id] = response

        return response


class Device:
    def __init__(self, device_id, device_manager, logger):
        self.device_id = device_id
        self.device_manager = device_manager
        self.logger = logger

        self.obj = self.device_manager.devices.get(self.device_id)

        self.expected_usage = 0
        self.expected_activity = None

        self.lock = None

        self.logger.info(f"Successfully created {self.__str__()}")

    def get_usage(self, if_on=False):
        """
        uses expected power usage and expected on times to return the power usage, 0 when off
        :return: Current power usage
        """
        if self.any or if_on:
            # If no expected activity list is defined:
            if self.expected_activity is None:
                # return usage
                return self.expected_usage

            # Else (Specific activity list)
            else:
                # For each active time:
                for active_time in self.expected_activity:
                    # If we are in an active time: return expected usage
                    if active_time.get('start') < datetime.now().time() < active_time.get('end'):
                        return self.expected_usage

                return 0
        else:
            return 0

    @property
    def any(self):
        # If the main is on: return True
        if self.switch == 'on':
            return True

        # For each outlet:
        for outlet in (self.switches or []):
            # If the outlet is on: return True
            if outlet.get('switch') == 'on':
                return True

        return False

    def shutdown(self):
        # If main is on, turn off
        if self.switch == 'on':
            self.off()

        # For each outlet:
        for outlet in (self.switches or []):
            # If the switch is on, turn it off:
            if outlet.get('switch') == 'on':
                self.off(outlet.get('outlet'))

    def startup(self):
        # If the main switch WAS on, and isnt anymore, turn on
        if self.switch == 'off':
            self.on()

        # For each outlet:
        for outlet in (self.switches or []):
            # If the switch is on, turn it off:
            if outlet.get('switch') == 'off':
                self.on(outlet.get('outlet'))

    def on(self, outlet=-1):
        try:
            self.set_switch('on', outlet)
        except Exception as e:
            self.logger.error(f"\tFailed to turn switch on {e}, refreshing login and seeing if that fixes it")
            self.device_manager.login()
            self.set_switch('on', outlet)

    def off(self, outlet=-1):
        try:
            self.set_switch('off', outlet)
        except Exception as e:
            self.logger.error(f"\tFailed to turn switch off {e}, refreshing login and seeing if that fixes it")
            self.device_manager.login()
            self.set_switch('off', outlet)

    def set_switch(self, state, outlet=-1):
        if self.device_manager.dev_mode:
            return
        body = {
            "deviceid": self.device_id,
            "params": {
            },
            "appid": APP_ID,
            "nonce": self.device_manager.generate_nonce(15),
            "ts": time.time(),
            "version": 8
        }

        if outlet == -1 and self.switch is not None:
            body['params'].update({
                'switch': state
            })
        elif outlet != -1 and self.switches is not None:
            switches = self.switches
            for switch in switches:
                if switch.get('outlet') == outlet:
                    switch.update({'switch': state})
            body['params'].update({
                'switches': switches
            })
        else:
            error_message = f"Trying to set {self.name}'s outlet {outlet} to '{state}', but that is not possible"
            self.logger.error(error_message)
            raise Exception(error_message)

        request = requests.post(f'https://eu-api.coolkit.cc:8080/api/user/device/status',
                                headers=self.device_manager.headers, json=json.dumps(body))

        response = request.json()

        self.logger.debug(f"Set switch request responded with {response}")

        if 'error' in response and response.get('error') != 0:
            error_message = f"There was an issue when trying to switch {self.name}"
            self.logger.error(error_message)
            raise Exception(error_message)
        else:
            self.refresh()
            self.logger.debug(f"Successfully turned {self.name} {state}")

    def refresh(self):
        self.obj = self.device_manager.devices.get(self.device_id)

    @property
    def name(self):
        return self.obj.get('name')

    @property
    def switch(self):
        self.refresh()
        _params = self.obj.get('params')
        if _params:
            return _params.get('switch')

    @property
    def switches(self):
        self.refresh()
        _params = self.obj.get('params')
        if _params:
            return _params.get('switches')

    @property
    def power(self):
        self.refresh()
        _params = self.obj.get('params')
        if _params.get('power') is not None:
            power = _params.get('power')
            return str(power/100) if not isinstance(power, str) else power

    def __outlet(self, index):
        _switches = self.switches
        if _switches:
            try:
                return list(filter(lambda x: x.get('outlet') == index, _switches))[0].get('switch')
            except Exception as e:
                return None

    def toggle(self, outlet=-1):
        if outlet == -1:
            if self.switch == 'off':
                self.on()
            elif self.switch == 'on':
                self.off()
            else:
                raise Exception('Trying to toggle a device outlet that returns None')
        else:
            if self.__outlet(outlet) == 'off':
                self.on(outlet)
            elif self.__outlet(outlet) == 'on':
                self.off(outlet)
            else:
                raise Exception('Trying to toggle a device outlet that returns None')

        self.device_manager.hard_reload_device(self.device_id)

    def __str__(self):
        return f"<{self.name} Device>"


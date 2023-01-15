import time
import random
import hmac
import json
import hashlib
import base64
import requests

APP_ID = 'YzfeftUVcZ6twZw1OoVKPRFYTrGEg01Q'
APP_SECRET = '4G91qSoboqYO4Y0XJ0LPPKIsq8reHdfa'


class DeviceManager:
    def __init__(self):
        self.headers = None
        self.bearer_token = None
        self.user_apikey = None
        self.logger = None

        self.login()

    @staticmethod
    def generate_nonce(length=8):
        """Generate pseudorandom number."""
        return ''.join([str(random.randint(0, 9)) for i in range(length)])

    def login(self, credentials_file='credentials.csv'):
        with open(credentials_file, 'r') as f:
            credentials = f.readline()
            email, password = credentials.split(',')

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

        request = requests.post('https://eu-api.coolkit.cc:8080/api/user/login',
                                headers=self.headers, json=body)

        response = request.json()
        if 'error' in response:
            raise Exception(f"Could not log into eWeLink: ({request.status_code}) {response}")

        self.bearer_token = response['at']
        self.user_apikey = response['user']['apikey']
        self.headers.update({'Authorization': 'Bearer ' + self.bearer_token})

        return True

    def get_devices(self):
        params = {
            "lang": 'en',
            "appid": "YzfeftUVcZ6twZw1OoVKPRFYTrGEg01Q",
            "ts": time.time(),
            "version": 8,
            "getTags": 1,
        }
        url_params = "&".join(["{}={}".format(param, params.get(param)) for param in params])
        request = requests.get(f'https://eu-api.coolkit.cc:8080/api/user/device?{url_params}',
                               headers=self.headers)

        response = request.json()

        return response.get('devicelist')

    def get_device(self, device_id):
        params = {
            "deviceid": device_id,
            "appid": APP_ID,
            "version": 8,
            "ts": time.time(),
        }
        url_params = "&".join(["{}={}".format(param, params.get(param)) for param in params])
        request = requests.get(f'https://eu-api.coolkit.cc:8080/api/user/device/{device_id}?{url_params}',
                               headers=self.headers)

        response = request.json()

        if 'error' in response and response.get('error') != 0:
            raise Exception(f"Error while getting device {device_id}, {response}")

        return response


class Device:
    device_manager = DeviceManager()
    __refresh_timer = 30
    logger = None

    class NoLoggerException(Exception):
        pass

    class SetSwitchFailedException(Exception):
        pass

    def __init__(self, device_id):
        if self.logger is None:
            raise self.NoLoggerException("Predefine the static logger for all Devices before creating an instance")
        else:
            if self.device_manager.logger is None:
                self.device_manager.logger = self.logger

        self.__device_id = device_id
        device_obj = self.device_manager.get_device(self.__device_id)
        self.last_refresh = time.time()
        self.obj = device_obj

        self.logger.info(f"Successfully created {self.__str__()}")

    def on(self, outlet=-1):
        try:
            self.set_switch('on', outlet)
        except Exception as e:
            self.logger.warning(f"\tFailed to turn switch on {e}, refreshing login and seeing if that fixes it")
            self.device_manager.login()
            self.set_switch('on', outlet)

    def off(self, outlet=-1):
        try:
            self.set_switch('off', outlet)
        except Exception as e:
            self.logger.warning(f"\tFailed to turn switch off {e}, refreshing login and seeing if that fixes it")
            self.device_manager.login()
            self.set_switch('off', outlet)

    def set_switch(self, state, outlet=-1):
        body = {
            "deviceid": self.device_id,
            "params": {
                "switch": state
            },
            "appid": APP_ID,
            "nonce": self.device_manager.generate_nonce(15),
            "ts": time.time(),
            "version": 8
        }
        if self.__switches and outlet != -1:
            switches = self.__switches
            for switch in switches:
                if switch.get('outlet') == outlet:
                    switch.update({'switch': state})
            body.update({'params': {"switches": switches}})
        elif self.__switches and outlet == -1:
            self.logger.error(f"Trying to set a mutli-channel switch with no outlet specified")
            raise Exception(f"Trying to set a mutli-channel switch with no outlet specified")

        request = requests.post(f'https://eu-api.coolkit.cc:8080/api/user/device/status',
                                headers=self.device_manager.headers, json=json.dumps(body))

        response = request.json()

        self.refresh(True)

        if 'error' in response and response.get('error') != 0:
            error_message = f"There was an issue when trying to switch {self.name} {state}, {response.get('error')}: {response.get('errmsg')}"
            self.logger.error(error_message)
            self.logger.debug(response)
            raise self.SetSwitchFailedException(error_message)
        else:
            self.logger.debug(f"Successfully turned {self.name} {state}")

    def refresh(self, override=False):
        # If the last refresh was NOT in the last 30 seconds
        if time.time() - self.last_refresh > self.__refresh_timer or override:
            self.logger.debug(f"Refreshing {self.__str__()}")
            self.logger.debug(f"\tDevice Manager headers: {self.device_manager.headers}")
            device_obj = self.device_manager.get_device(self.__device_id)
            self.last_refresh = time.time()
            self.logger.debug(f"{self.__str__()} refreshed with: {device_obj}")
            self.obj = device_obj

    @property
    def name(self):
        return self.obj.get('name')

    @property
    def device_id(self):
        return self.obj.get('deviceid')

    @property
    def __switch(self):
        _params = self.obj.get('params')
        if _params:
            return _params.get('switch')

    @property
    def switch(self):
        if self.__switch is not None:
            self.refresh()
            _params = self.obj.get('params')
            if _params:
                return _params.get('switch')

    @property
    def __switches(self):
        _params = self.obj.get('params')
        if _params:
            return _params.get('switches')

    @property
    def switches(self):
        if self.__switches is not None:
            self.refresh()
            _params = self.obj.get('params')
            if _params:
                return _params.get('switches')

    @property
    def power(self):
        _params = self.obj.get('params')
        if _params.get('power'):
            self.refresh()
            power = _params.get('power')
            return str(power/100) if not isinstance(power, str) else power

    def __str__(self):
        return f"<{self.name} Device>"


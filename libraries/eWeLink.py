import time
import random
import hmac
import json
import hashlib
import base64
import requests
from datetime import datetime

APP_ID = 'YzfeftUVcZ6twZw1OoVKPRFYTrGEg01Q'
APP_SECRET = '4G91qSoboqYO4Y0XJ0LPPKIsq8reHdfa'


class DeviceManager:
    logger = None

    def __init__(self):
        self.headers = None
        self.bearer_token = None
        self.user_apikey = None

        self.login()

    @staticmethod
    def generate_nonce(length=8):
        """Generate pseudorandom number."""
        return ''.join([str(random.randint(0, 9)) for i in range(length)])

    def login(self, credentials_file='credentials.csv'):
        self.logger.debug("Logging into eWeLink")
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

        self.logger.debug(f"Getting bearer token, headers: {self.headers}, body: {body}")
        request = requests.post('https://eu-api.coolkit.cc:8080/api/user/login',
                                headers=self.headers, json=body)

        response = request.json()
        if 'error' in response:
            raise Exception(f"Could not log into eWeLink: ({request.status_code}) {response}")

        self.logger.debug(f"eWeLink API responded with: {response}")
        self.bearer_token = response['at']
        self.user_apikey = response['user']['apikey']
        self.headers.update({'Authorization': 'Bearer ' + self.bearer_token})

        self.logger.debug(f"Headers updated to: {self.headers}")

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
    device_manager = None
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
            if self.device_manager is None:
                DeviceManager.logger = self.logger
                Device.device_manager = DeviceManager()

        self.__device_id = device_id
        device_obj = self.device_manager.get_device(self.__device_id)
        self.last_refresh = time.time()
        self.obj = device_obj

        self.expected_usage = 0
        self.expected_activity = None
        self.shutdown_state = {}

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
        # Store current state for self.restore later
        self.shutdown_state = {
            'switch': self.switch,
            'switches': self.switches,
        }

        # If main is on, turn off
        if self.switch == 'on':
            self.off()

        # For each outlet:
        for outlet in (self.switches or []):
            # If the switch is on, turn it off:
            if outlet.get('switch') == 'on':
                self.off(outlet.get('outlet'))

    def restore(self):
        # If the main switch WAS on, and isnt anymore, turn on
        _switch = self.shutdown_state.get('switch')
        if _switch == 'on' and self.switch == 'off':
            self.on()

        # For all the outlets, if they WERE on, and arent anymore, turn on
        restore_outlets = self.shutdown_state.get('switches') or []
        current_outlets = self.switches or []

        for i in range(current_outlets):
            if restore_outlets[i].get('switch') == 'on' and current_outlets[i].get('switch') == 'off':
                self.on(current_outlets[i].get('outlet'))

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

        self.refresh(0)

        if 'error' in response and response.get('error') != 0:
            error_message = f"There was an issue when trying to switch {self.name} {state}, {response.get('error')}: {response.get('errmsg')}"
            self.logger.error(error_message)
            self.logger.debug(response)
            raise self.SetSwitchFailedException(error_message)
        else:
            self.logger.debug(f"Successfully turned {self.name} {state}")

    def refresh(self, refresh_timer=__refresh_timer):
        # If the last refresh was NOT in the last 30 seconds
        if time.time() - self.last_refresh > refresh_timer:
            self.logger.debug(f"Refreshing {self.__str__()}")
            device_obj = self.device_manager.get_device(self.__device_id)
            self.last_refresh = time.time()
            self.logger.debug(f"{self.__str__()} refreshed")
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

    def __outlet(self, index):
        _switches = self.__switches
        if _switches:
            try:
                return list(filter(lambda x: x.get('outlet') == index, _switches))[0].get('switch')
            except Exception as e:
                return None

    def toggle(self, outlet=-1):
        if outlet == -1:
            if self.__switch == 'off':
                self.on()
            elif self.__switch == 'on':
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

    def __str__(self):
        return f"<{self.name} Device>"


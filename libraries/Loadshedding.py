from datetime import datetime, timedelta
import time
import requests


class Tracker:
    logger = None
    __refresh_delay = 600

    def __init__(self, schedule_file):
        self.schedule = []
        self.times = []

        self.parse(schedule_file)
        self.__last_check = None
        self.__stage = 0

    @property
    def stage(self):
        # Refresh the internal loadshedding stage only if enough time has passed
        if not self.__last_check or time.time() - self.__last_check > self.__refresh_delay:
            self.logger.debug(f"Refreshing loadshedding stage")
            response = requests.get("https://loadshedding.eskom.co.za/LoadShedding/GetStatus")
            self.__last_check = time.time()
            self.__stage = response.json()

        return self.__stage

    def get_next(self):
        self.logger.debug("Getting time until next loadshedding schedule")

        # Get now's date and time
        now = datetime.now()

        # Get datetime objects of all loadshedding for TODAY in the format [start, end]
        today_slots = [
            (
                datetime.fromisoformat(f"{now.year}-{str(now.month).zfill(2)}-{str(now.day).zfill(2)}T{_time[0]}"),
                datetime.fromisoformat(f"{now.year}-{str(now.month).zfill(2)}-{str(now.day).zfill(2)}T{_time[1]}")
            )
            for _time in self.times
        ]
        # Fix issue if last slot starts and ends in two different days
        today_slots = [[s[0], s[1] + timedelta(days=1)] if s[1] < s[0] else [s[0], s[1]] for s in today_slots]

        # Get datetime objects of all loadshedding for TOMORROW in the format [start, end]
        tomorrow_slots = [
            (
                datetime.fromisoformat(f"{now.year}-{str(now.month).zfill(2)}-{str((now.day+1) % 31).zfill(2)}T{_time[0]}"),
                datetime.fromisoformat(f"{now.year}-{str(now.month).zfill(2)}-{str((now.day+1) % 31).zfill(2)}T{_time[1]}")
            )
            for _time in self.times
        ]
        # Fix issue if last slot starts and ends in two different days
        tomorrow_slots = [[s[0], s[1] + timedelta(days=1)] if s[1] < s[0] else [s[0], s[1]] for s in tomorrow_slots]

        # Get list of slots that will occur, in the format of a boolean list
        current_stage = self.stage
        today_stages = [r[2::][(now.day-1) % 31] for r in self.schedule[1::]]
        today_stages = [True if int(stage) <= current_stage and stage != '0' else False for stage in today_stages]
        tomorrow_stages = [r[2::][now.day % 31] for r in self.schedule[1::]]
        tomorrow_stages = [True if int(stage) <= current_stage and stage != '0' else False for stage in tomorrow_stages]

        # Combine today and tomorrow's slots into datetime list
        loadshedding_times = [today_slots[i] for i in range(len(today_stages)) if today_stages[i]] + [tomorrow_slots[i] for i in range(len(tomorrow_stages)) if tomorrow_stages[i]]

        # This section of code joins neighbouring sessions together
        i = 0
        while i < (len(loadshedding_times)-1):
            if loadshedding_times[i][1] > loadshedding_times[i+1][0]:
                loadshedding_times[i] = (loadshedding_times[i][0], loadshedding_times[i+1][1])
                loadshedding_times.pop(i+1)

            i += 1

        # Get current or closest upcoming loadshedding schedule
        for loadshedding_window in loadshedding_times:
            # If you are in this loadshedding schedule
            if loadshedding_window[0] < now < loadshedding_window[1]:
                return {
                    "start": 0,
                    "end": (loadshedding_window[1] - now).total_seconds()/3600,
                    "duration": (loadshedding_window[1] - now).total_seconds()/3600,
                    "_start": loadshedding_window[0],
                    "_end": loadshedding_window[1],
                }

            # Else if this one is upcoming
            if now < loadshedding_window[0]:
                return {
                    "start": (loadshedding_window[0] - now).total_seconds()/3600,
                    "end": (loadshedding_window[1] - now).total_seconds()/3600,
                    "duration": (loadshedding_window[1] - loadshedding_window[0]).total_seconds()/3600,
                    "_start": loadshedding_window[0],
                    "_end": loadshedding_window[1],
                }

        return None

    def parse(self, schedule_file):
        # Read schedule
        with open(schedule_file, 'r') as file:
            file_content = file.read()
            rows = file_content.split('\n')
            # If csv ends with a \n, the last index isn't an entry
            if rows[-1] == '':
                rows.pop(-1)

        self.schedule = [r.split(',') for r in rows]
        self.times = [r[0:2] for r in self.schedule[1:]]

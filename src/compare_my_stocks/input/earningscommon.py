import json
import time

import pytz
import requests

from config import config


class RapidApi:
    def __init__(self):
        name=(self.__class__.__name__)
        headersconf= name + "Headers"
        self.headers=getattr(config, headersconf)
    def is_initialized(self):
        return self.headers.get("X-RapidAPI-Key") is not None
    def get_json(self,querystring, url):
        response = requests.request("GET", url, headers=self.headers, params=querystring)
        t = json.loads(response.text)
        time.sleep(0.21)
        return t


localize_me = lambda x: (pytz.UTC.localize(x, True) if not x.tzinfo else x)
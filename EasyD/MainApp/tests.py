from django.test import TestCase
from MainApp.views import user_info
from pymongo import MongoClient
import requests


def fetch_events():
    url = "https://www.eventbriteapi.com/v3/events/search/"
    params = {
        "location.address": "New Delhi",
        "location.within": "10km",
        "token": "U2AXLKSCZKURLLLCDP"
    }
    response = requests.get(url, params=params)
    return response.json().get("events", [])

events = fetch_events()
print(events)

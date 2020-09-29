import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import base64
from collections import namedtuple
from flask_restful import Api, Resource, reqparse

from config import credentials
import requests
from config import DISCORD_WEBHOOK_URL

def is_local():
    import socket
    import os

    hostname = socket.gethostname()
    isLocal = None
    if hostname[:7] == "DESKTOP" or hostname[:5] == "Chuns":
        isLocal = True
    else:
        isLocal = False

    return isLocal


def fetch_spread_sheet():
    from app.cache import cache
    gc = gspread.authorize(credentials).open("문학따먹기")

    wks = gc.get_worksheet(0)

    rows = wks.get_all_values()
    print(rows)
    Munhak = namedtuple("Munhak", rows[0])
    try:

        data = []
        for row in rows[1:]:
            # row_tuple = Munhak(*row)
            # row_tuple = row_tuple._replace(keywords=json.loads(row_tuple.keywords))
            # if row_tuple.is_available == "TRUE":
            #     data.append(row_tuple)
            temp_dict = dict(zip(rows[0], row))
            if temp_dict["is_available"] == "TRUE":
                temp_dict["keywords"] = json.loads(temp_dict["keywords"])
                temp_dict["munhak_seq"] = int(temp_dict["munhak_seq"])
                data.append(temp_dict)

    except:
        pass

    # global munhak_rows_data
    munhak_rows_data = data
    cache.set('munhak_rows_data', data, timeout=99999999999999999)
    print(data)
    # print(munhak_rows)
    return len(data)


def format_url_title(title):
    return title.replace(" ", "-")


def send_discord_webhook(webhook_body):
    requests.post(
        DISCORD_WEBHOOK_URL,
        json=webhook_body)
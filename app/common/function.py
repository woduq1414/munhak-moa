import smtplib
import threading
from email.mime.multipart import MIMEMultipart

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import base64
from collections import namedtuple
from flask_restful import Api, Resource, reqparse
from datetime import datetime
from config import credentials
import requests
from config import DISCORD_WEBHOOK_URL
from flask import request
import ssl


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
    # print(rows)
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

                if temp_dict["title"] == "" or temp_dict["writer"] == "":
                    break

                temp_dict["keywords"] = json.loads(temp_dict["keywords"])
                temp_dict["munhak_seq"] = int(temp_dict["munhak_seq"])
                data.append(temp_dict)

    except:
        pass

    # global munhak_rows_data
    munhak_rows_data = data

    munhak_quiz_rows_data = [munhak_row for munhak_row in munhak_rows_data if len(munhak_row["keywords"]) != 0]

    munhak_rows_data_dict = {}
    for munhak_row in munhak_rows_data:
        munhak_rows_data_dict[munhak_row["munhak_seq"]] = munhak_row

    cache.set('munhak_rows_data', munhak_rows_data, timeout=99999999999999999)
    cache.set('munhak_rows_data_dict', munhak_rows_data_dict, timeout=99999999999999999)

    cache.set('munhak_quiz_rows_data', munhak_quiz_rows_data, timeout=99999999999999999)
    # print(data)
    # print(munhak_rows)
    return len(data)


def format_url_title(title):
    return title.replace(" ", "-")


def send_discord_webhook(webhook_body):
    requests.post(
        DISCORD_WEBHOOK_URL,
        json=webhook_body)


def get_ip_address():
    return request.headers[
        'X-Forwarded-For'] if 'X-Forwarded-For' in request.headers else request.remote_addr


def send_discord_alert_log(alert_string):
    from flask import request, g, session
    webhook_body = {

        "embeds": [
            {
                "title": "=========ALERT=========",
                "color": 14177041

            },
            {
                "description": alert_string
            },
            {
                "fields": [
                    {
                        "name": "URI",
                        "value": request.url,
                        "inline": True
                    },
                    {
                        "name": "User",
                        "value": session.get("user").__str__(),
                        "inline": True
                    },

                ],
                "color": 0

            },

            {
                "title": str(datetime.now()) + ", " + (
                    "로컬에서 발생" if is_local() else "외부에서 발생") + ", " + get_ip_address(),
                "color": 0
            },

        ]
    }
    threading.Thread(target=lambda: send_discord_webhook(webhook_body=webhook_body)).start()


def edit_distance(s1, s2):
    l1, l2 = len(s1), len(s2)
    if l2 > l1:
        return edit_distance(s2, s1)
    if l2 is 0:
        return l1
    prev_row = list(range(l2 + 1))
    current_row = [0] * (l2 + 1)
    for i, c1 in enumerate(s1):
        current_row[0] = i + 1
        for j, c2 in enumerate(s2):
            d_ins = current_row[j] + 1
            d_del = prev_row[j + 1] + 1
            d_sub = prev_row[j] + (1 if c1 != c2 else 0)
            current_row[j + 1] = min(d_ins, d_del, d_sub)
        prev_row[:] = current_row[:]
    return prev_row[-1]

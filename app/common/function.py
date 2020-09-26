import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import base64
from collections import namedtuple
from flask_restful import Api, Resource, reqparse

from config import credentials


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


def get_munhak_video_list(munhak_title):
    import requests
    from config import YOUTUBE_KEY

    munhak_video_list = []
    res = requests.get("https://www.googleapis.com/youtube/v3/search", params={
        "key": YOUTUBE_KEY, "part": "snippet", "q": munhak_title + " 해설", "maxResults": 10
    })

    if res.status_code != 200:
        return []

    video_data_list = json.loads(res.text)["items"]

    word_list = ["강의", "학평", "모평", "모의고사", "학력평가", "수능", "해설", "뿐석", "수특", "수능특강", "기출"]
    for video in video_data_list:
        video_title = video["snippet"]["title"]
        print(video_title)
        video_description = video["snippet"]["description"]
        if (munhak_title in video_title) and any((word in video_title) for word in word_list):

            video["snippet"]["title"] = video["snippet"]["title"].replace("&#39;", "'")

            munhak_video_list.append(video)

    return munhak_video_list


def get_exam_video_list(source):
    import requests
    from config import YOUTUBE_KEY

    exam_video_list = []
    res = requests.get("https://www.googleapis.com/youtube/v3/search", params={
        "key": YOUTUBE_KEY, "part": "snippet", "q": source + " 국어", "maxResults": 10
    })

    if res.status_code != 200:
        return []

    video_data_list = json.loads(res.text)["items"]

    word_list = ["강의", "학평", "모평", "모의고사", "학력평가", "수능", "해설", "뿐석", "수특", "수능특강", "기출"]
    for video in video_data_list:
        video_title = video["snippet"]["title"]
        print(video_title)
        video_description = video["snippet"]["description"]
        if any((word in video_title) for word in word_list):
            exam_video_list.append(video)

    return  exam_video_list

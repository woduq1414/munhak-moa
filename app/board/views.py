from flask import Blueprint
from flask import Flask, render_template, session, request, flash, redirect, url_for, Response, abort, jsonify, \
    send_file
import socket
import os
import random
import copy
# from app.global_var import munhak_rows_data
from flask_sqlalchemy import SQLAlchemy, Model
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import base64
from collections import namedtuple
from flask_restful import Api, Resource, reqparse

from config import credentials, SECRET_KEY, YOUTUBE_KEY
from app.cache import cache
from app.common.function import *
import requests

board_bp = Blueprint('board', __name__)


@board_bp.route('/test')
def test():
    return render_template("test.html")


@board_bp.route('/board/detail/<int:munhak_seq>/<munhak_title>/')
@board_bp.route('/board/detail/<int:munhak_seq>/', defaults={'munhak_title': None})
def munhak_board_detail(munhak_seq, munhak_title):
    munhak_rows_data = cache.get("munhak_rows_data")
    munhak_rows = copy.deepcopy(munhak_rows_data)

    target_munhak_row = None
    for munhak_row in munhak_rows:
        if munhak_row["munhak_seq"] == munhak_seq:
            target_munhak_row = munhak_row
    print(munhak_rows)
    print(target_munhak_row)
    if target_munhak_row is None:
        return render_template("munhak_board_detail_404.html")

    if munhak_title != format_url_title(target_munhak_row["title"]):
        return redirect(url_for('board.munhak_board_detail', munhak_seq=munhak_seq,
                                munhak_title=format_url_title(target_munhak_row["title"])))

    munhak_video_list = get_munhak_video_list(munhak_title)
    exam_video_list = get_exam_video_list(target_munhak_row["source"])







    print(munhak_video_list)
    print(exam_video_list)


    data = {
        "munhak_seq": munhak_seq,
        "title": target_munhak_row["title"],
        "writer": target_munhak_row["writer"],
        "source": target_munhak_row["source"],
        "category": target_munhak_row["category"],
        "munhak_video_list" : munhak_video_list[:2],
        "exam_video_list" : exam_video_list
    }
    return render_template("munhak_board_detail.html", data=data)

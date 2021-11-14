from flask import Blueprint, make_response
from flask import Flask, render_template, session, request, flash, redirect, url_for, Response, abort, jsonify, \
    send_file
import socket
from datetime import datetime
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
from sqlalchemy import func, desc, asc

from app.common.decorator import return_500_if_errors, login_required
from app.db import *
from config import credentials, SECRET_KEY
from app.cache import cache
from app.common.function import fetch_spread_sheet, format_url_title, send_discord_alert_log
from config import SECRET_KEY
import random
from collections import defaultdict

toto_bp = Blueprint('toto', __name__)


def is_toto_target_munhak(munhak_row):
    if munhak_row["source"] == "2022학년도 수능특강" or munhak_row["source"] == "2022학년도 수능완성":
        return True
    else:
        return False


@toto_bp.route('/')
def toto_index():
    munhak_rows_data_dict = cache.get("munhak_rows_data_dict")
    pick_deadline = datetime(2021, 11, 16, 23, 59, 59)
    toto_real_result = [120, 122, 124, 126, 128, 130]
    is_result_open = False

    data = {

    }
    data["is_result_open"] = is_result_open

    try:
        user_seq = session["user"]["user_seq"]
    except:
        user_seq = None
    data["user_seq"] = user_seq

    print(data)

    if datetime.now() < pick_deadline:
        # 픽 가능
        data["is_pick_available"] = True
        pick_rows = TotoPick.query.all()

        pick_list = [{
            "nickname": x.user.nickname, "pick1": munhak_rows_data_dict.get(x.pick1),
            "pick2": munhak_rows_data_dict.get(x.pick2), "pick3": munhak_rows_data_dict.get(x.pick3),
            "pick4": munhak_rows_data_dict.get(x.pick4),
            "pick5": munhak_rows_data_dict.get(x.pick5), "pick6": munhak_rows_data_dict.get(x.pick6),
            "date": x.add_date.strftime("%Y-%m-%d"), "user_seq": x.user.user_seq
        } for x in pick_rows]

        print(pick_list)

        random.shuffle(pick_list)
        data["pick_list"] = pick_list

        resp = make_response(render_template("toto/index.html", data=data))
        resp.set_cookie('PJAX-URL', base64.b64encode(request.url.encode("UTF-8")), max_age=None, expires=None, path='/')
        return resp
    else:
        # 픽 종료
        data["is_pick_available"] = False
        if is_result_open:
            pass
        else:
            pick_rows = TotoPick.query.all()

            pick_list = [{
                "nickname": x.user.nickname, "pick1": munhak_rows_data_dict.get(x.pick1),
                "pick2": munhak_rows_data_dict.get(x.pick2), "pick3": munhak_rows_data_dict.get(x.pick3),
                "pick4": munhak_rows_data_dict.get(x.pick4),
                "pick5": munhak_rows_data_dict.get(x.pick5), "pick6": munhak_rows_data_dict.get(x.pick6),
                "date": x.add_date.strftime("%Y-%m-%d"), "user_seq": x.user.user_seq
            } for x in pick_rows]

            random.shuffle(pick_list)
            data["pick_list"] = pick_list

            resp = make_response(render_template("toto/index.html", data=data))
            resp.set_cookie('PJAX-URL', base64.b64encode(request.url.encode("UTF-8")), max_age=None, expires=None,
                            path='/')
            return resp


@toto_bp.route('/detail/<int:munhak_seq>/')
def toto_munhak_detail(munhak_seq):
    data = {}

    munhak_rows = cache.get("munhak_rows_data")
    munhak_rows_data_dict = cache.get("munhak_rows_data_dict")

    target_munhak_row = munhak_rows_data_dict.get(munhak_seq, None)
    if target_munhak_row is None:
        return abort(404)

    data["munhak_row"] = target_munhak_row

    title_same_rows = []
    writer_same_rows = []

    for munhak_row in munhak_rows:
        if target_munhak_row["title"] == munhak_row["title"]:
            title_same_rows.append(munhak_row)
        elif target_munhak_row["writer"] != "작자 미상" and target_munhak_row["writer"] == munhak_row["writer"]:
            writer_same_rows.append(munhak_row)
    data["title_same_rows"] = list(reversed(title_same_rows))
    data["writer_same_rows"] = list(reversed(writer_same_rows))

    return jsonify(data)


@toto_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_pick():
    user_seq = session["user"]["user_seq"]
    args = request.form

    pick_list_tmp = [args.get(f"pick{i}", "NaN") for i in range(1, 7)]
    pick_list = []
    for pick in pick_list_tmp:
        if pick == "NaN":
            pick_list.append(None)
        else:
            pick_list.append(int(pick))

    print(args, pick_list)
    # return

    if len(pick_list) != 6:
        return abort(400)

    pick_list_not_none = [x for x in pick_list if x is not None]

    if not len(pick_list_not_none) >= 2 and len(pick_list_not_none) <= 6:
        print("@#@#$")
        return abort(400)

    if len(set(pick_list_not_none)) != len(pick_list_not_none):
        return abort(400)

    munhak_rows_data = cache.get("munhak_rows_data")
    munhak_rows = copy.deepcopy(munhak_rows_data)

    for pick in pick_list_not_none:
        munhak_row = [x for x in munhak_rows if x["munhak_seq"] == pick and is_toto_target_munhak(x)]
        print(munhak_row, pick)
        if len(munhak_row) == 0:
            return abort(404)

    old_pick_row = TotoPick.query.filter_by(user_seq=user_seq).first()
    if old_pick_row is not None:
        db.session.delete(old_pick_row)

    pick_row = TotoPick(
        user_seq=user_seq,
        pick1=pick_list[0],
        pick2=pick_list[1],
        pick3=pick_list[2],
        pick4=pick_list[3],
        pick5=pick_list[4],
        pick6=pick_list[5],
        add_date=datetime.now(),
    )

    db.session.add(pick_row)
    db.session.commit()

    send_discord_alert_log(f"Pick add! {str(pick_list)}")

    return "", 200


@toto_bp.route("/delete", methods=["GET", "POST"])
@login_required
def delete_pick():
    user_seq = session["user"]["user_seq"]

    old_pick_row = TotoPick.query.filter_by(user_seq=user_seq).first()
    if old_pick_row is None:
        return abort(404)

    db.session.delete(old_pick_row)
    db.session.commit()
    return "", 200


@toto_bp.route("/pick", methods=["GET", "POST"])
@login_required
def pick_toto_form():
    munhak_rows_data = cache.get("munhak_rows_data")
    munhak_rows_data_dict = cache.get("munhak_rows_data_dict")

    munhak_rows = copy.deepcopy(munhak_rows_data)

    user_seq = session["user"]["user_seq"]

    data = {

    }
    munhak_group_data = defaultdict(list)
    for munhak_row in munhak_rows:
        if is_toto_target_munhak(munhak_row):
            munhak_group_data[munhak_row["category"]].append(munhak_row)
    data["munhak_group_data"] = munhak_group_data

    old_pick_data = []

    old_pick_row = TotoPick.query.filter_by(user_seq=user_seq).first()
    if old_pick_row is not None:
        for pick in [old_pick_row.pick1, old_pick_row.pick2, old_pick_row.pick3, old_pick_row.pick4, old_pick_row.pick5,
                     old_pick_row.pick6]:
            if pick is not None:
                old_pick_data.append(munhak_rows_data_dict[pick])

    data["old_pick_data"] = old_pick_data
    print(data)

    r = make_response(render_template("./toto/toto_form.html", data=data))
    r.set_cookie('PJAX-URL', base64.b64encode(request.url.encode("UTF-8")), max_age=None, expires=None, path='/')
    return r

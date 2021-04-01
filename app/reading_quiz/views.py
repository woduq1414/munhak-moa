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
from sqlalchemy import func

from app.common.decorator import return_500_if_errors, login_required
from app.db import *
from config import credentials, SECRET_KEY
from app.cache import cache
from app.common.function import fetch_spread_sheet, format_url_title, send_discord_alert_log
from config import SECRET_KEY

reading_quiz_bp = Blueprint('reading_quiz', __name__)


@reading_quiz_bp.route('/list')
def reading_quiz_list():
    data = {}

    # munhak_rows = ContentQuizMunhak.query.all()
    #
    # munhak_list = [x.as_dict() for x in munhak_rows]
    munhak_rows = db.session.query(ContentQuizMunhak, func.count(ContentQuiz.quiz_seq).label("quiz_count")).outerjoin(
        ContentQuiz,
        ContentQuiz.munhak_seq == ContentQuizMunhak.munhak_seq).group_by(ContentQuizMunhak.munhak_seq).all()

    print(munhak_rows)

    # # return "DD"
    # tips = [dict(tip_row.Tip.as_dict(),
    #              **{"like_count": tip_row.like_count, "liked": "true" if tip_row.liked == 1 else "false",
    #                 "is_mine": "true" if tip_row.Tip.user_seq == user_seq else "false",
    #                 "user_nickname": tip_row.Tip.user.nickname}, ) for
    #         tip_row in tip_rows]


    data["munhak_list"] = munhak_rows

    print(data)

    resp = make_response(render_template("reading_quiz_list.html", data=data))
    resp.set_cookie('PJAX-URL', base64.b64encode(request.url.encode("UTF-8")), max_age=None, expires=None, path='/')
    return resp


@reading_quiz_bp.route('/detail/<int:munhak_seq>/<munhak_title>/')
@reading_quiz_bp.route('/detail/<int:munhak_seq>/', defaults={'munhak_title': None})
def reading_quiz_detail(munhak_seq, munhak_title):
    if "user" in session:
        user_seq = session["user"]["user_seq"]
    else:
        user_seq = -1

    munhak_rows = ContentQuizMunhak.query.all()

    target_munhak_row = None
    for munhak_row in munhak_rows:
        if munhak_row.munhak_seq == munhak_seq:
            target_munhak_row = munhak_row

    if target_munhak_row is None:
        return render_template("munhak_board_detail_404.html")

    if munhak_title != format_url_title(target_munhak_row.title):
        return redirect(url_for('reading_quiz.reading_quiz_detail', munhak_seq=munhak_seq,
                                munhak_title=format_url_title(target_munhak_row.title)))

    quiz_rows = ContentQuiz.query.filter_by(munhak_seq=munhak_seq).all()

    quiz_list = [dict(quiz_row.as_dict(),
                      **{
                          "is_mine": "true" if quiz_row.user_seq == user_seq else "false",
                          "user_nickname": quiz_row.user.nickname}, ) for
                 quiz_row in quiz_rows]

    print(quiz_list)

    quiz_mine_exist = False
    for quiz in quiz_list:
        quiz_mine_exist = quiz_mine_exist or (quiz["is_mine"] == "true")


    data = {
        "munhak_row": target_munhak_row,
        "quiz_list": quiz_list,
        "quiz_mine_exist": quiz_mine_exist,
    }

    r = make_response(render_template("reading_quiz_detail.html", data=data))
    r.set_cookie('PJAX-URL', base64.b64encode(request.url.encode("UTF-8")), max_age=None, expires=None, path='/')
    return r


@reading_quiz_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_reading_quiz():
    args = request.form
    munhak_seq = args.get("munhak_seq", None)
    content = args.get("content", None)
    print(args)
    if munhak_seq is None or not munhak_seq.isdigit() or content is None or type(content) != str:
        return abort(400)
    if not (1 <= len(content) <= 1000):
        return abort(400)
    munhak_seq = int(munhak_seq)


    munhak_row = ContentQuizMunhak.query.filter_by(munhak_seq=munhak_seq).first()
    if munhak_row is None:
        return abort(404)


    user_seq = session["user"]["user_seq"]

    old_quiz_row = ContentQuiz.query.filter_by(user_seq=user_seq, munhak_seq=munhak_seq).first()
    if old_quiz_row is not None:
        return abort(409)

    quiz_row = ContentQuiz(
        quiz_content=content,
        user_seq=user_seq,
        munhak_seq=munhak_seq,
        add_date=datetime.now(),
    )

    db.session.add(quiz_row)
    db.session.commit()

    send_discord_alert_log(f"새로운 퀴즈 추가! {quiz_row.munhak.title}")

    return "", 200


@reading_quiz_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit_reading_quiz():
    args = request.form
    munhak_seq = args.get("munhak_seq", None)
    content = args.get("content", None)
    print(args)
    if munhak_seq is None or not munhak_seq.isdigit() or content is None or type(content) != str:
        return abort(400)
    if not (1 <= len(content) <= 1000):
        return abort(400)
    munhak_seq = int(munhak_seq)

    munhak_row = ContentQuizMunhak.query.filter_by(munhak_seq=munhak_seq).first()
    if munhak_row is None:
        return abort(404)

    user_seq = session["user"]["user_seq"]

    old_quiz_row = ContentQuiz.query.filter_by(user_seq=user_seq, munhak_seq=munhak_seq).first()
    if old_quiz_row is None:
        return abort(404)

    old_quiz_row.quiz_content = content

    db.session.commit()
    
    send_discord_alert_log(f"퀴즈 수정! {old_quiz_row.munhak.title}")

    return "", 200



@reading_quiz_bp.route("/delete", methods=["GET", "POST"])
@login_required
def delete_reading_quiz():
    args = request.form
    reading_quiz_seq = args.get("reading_quiz_seq", None)
    print(args)
    if reading_quiz_seq is None or not reading_quiz_seq.isdigit():
        return abort(400)

    reading_quiz_seq = int(reading_quiz_seq)
    user_seq = session["user"]["user_seq"]

    old_quiz_row = ContentQuiz.query.filter_by(user_seq=user_seq, quiz_seq=reading_quiz_seq).first()
    if old_quiz_row is None:
        return abort(404)

    db.session.delete(old_quiz_row)
    db.session.commit()
    return "", 200


@reading_quiz_bp.route("/write/<int:munhak_seq>", methods=["GET", "POST"])
@login_required
def write_reading_quiz_form(munhak_seq):
    munhak_seq = munhak_seq

    munhak_rows_data = cache.get("munhak_rows_data")
    munhak_rows = copy.deepcopy(munhak_rows_data)

    munhak_row = ContentQuizMunhak.query.filter_by(munhak_seq=munhak_seq).first()
    if munhak_row is None:
        return abort(404)

    data = {
        "munhak_row": munhak_row
    }

    user_seq = session["user"]["user_seq"]
    quiz_row = ContentQuiz.query.filter_by(munhak_seq=munhak_seq, user_seq=user_seq).first()

    if quiz_row is not None:
        data["content"] = quiz_row.quiz_content
        print(data["content"])





    return render_template("reading_quiz_form.html", data=data)

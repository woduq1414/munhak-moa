from flask import Blueprint
from flask import Flask, render_template, session, request, flash, redirect, url_for, Response, abort, jsonify, \
    send_file, make_response
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

from app.common.decorator import return_500_if_errors, login_required
from config import credentials, SECRET_KEY, YOUTUBE_KEY
from app.cache import cache
from app.common.function import *
import requests
from app.db import *
import datetime
from datetime import datetime

user_bp = Blueprint('user', __name__)



@user_bp.route("/user/change-nickname", methods=["GET", "POST"])
@login_required
def change_nickname():
    args = request.form
    nickname = args.get("nickname", None)
    if nickname is None or (not (1 <= len(nickname.encode("cp949")) <= 16)):
        return abort(400)
    user_seq = session["user"]["user_seq"]
    user_row = User.query.filter_by(user_seq=user_seq).first()
    if user_row is None:
        return abort(401)

    user_row.nickname = nickname

    db.session.commit()

    session["user"] = user_row.as_dict()
    print(session)
    return jsonify({
        "message" : "정상적으로 처리되었습니다."
    }), 200



@user_bp.route('/my')
@login_required
def my_page():
    print(session["user"]["nickname"])
    resp = make_response(render_template("user/my_page.html"))
    resp.set_cookie('PJAX-URL', base64.b64encode(request.url.encode("UTF-8")), max_age=None, expires=None, path='/')
    return resp





@user_bp.route('/login')
def login_form():
    return render_template('user/login_form.html')



@user_bp.route('/register')
def register_form():
    return render_template('user/register_form.html')



@user_bp.route('/register-query', methods=["GET", "POST"])
def register_query():
    args = request.form
    nickname = args.get("nickname", None)
    if nickname is None or (not (1 <= len(nickname.encode("cp949")) <= 16)):
        return abort(400)
    cookies = request.cookies
    if "kakao-access-token" not in cookies:
        return abort(403)
    access_token = cookies["kakao-access-token"]
    if access_token is None or type(access_token) != str:
        return abort(400)

    res = requests.get("https://kapi.kakao.com/v1/user/access_token_info", headers={
        "Authorization": "Bearer " + access_token
    })

    kakao_id = str(json.loads(res.text)["id"])

    old_user_row = User.query.filter((User.nickname == nickname) | (User.social_id == kakao_id)).first()
    if old_user_row is not None:
        return abort(409)

    user_row = User(
        nickname=nickname,
        social_type="kakao",
        social_id=kakao_id,
        add_date=datetime.now()
    )
    db.session.add(user_row)
    db.session.commit()
    session["user"] = user_row.as_dict()

    send_discord_alert_log(f"새로운 회원! {nickname}")

    return make_response("", 200)



@user_bp.route('/login-query-kakao', methods=["GET", "POST"])
def login_query_kakao():


    args = request.form
    access_token = args.get("access_token", None)
    print(access_token)
    if access_token is None or type(access_token) != str:
        return abort(400)

    res = requests.get("https://kapi.kakao.com/v1/user/access_token_info", headers={
        "Authorization": "Bearer " + access_token
    })

    kakao_id = str(json.loads(res.text)["id"])

    user_row = User.query.filter_by(social_type="kakao", social_id=kakao_id).first()
    print(user_row)
    if user_row is None:
        print("SDSD")
        return abort(404)

    session["user"] = user_row.as_dict()




    return make_response("", 200)



@user_bp.route('/logout')
def logout():
    if "user" in session:
        del session["user"]
    return redirect(url_for('board.munhak_board_list'))

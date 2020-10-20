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
from sqlalchemy import desc, asc
import uuid

from app.common.encrypt import simpleEnDecrypt
from config import credentials, SECRET_KEY
from app.cache import cache
from app.common.function import fetch_spread_sheet, send_discord_alert_log
from app.db import *

quiz_bp = Blueprint('quiz', __name__)
from datetime import datetime


@quiz_bp.route('/')
def index():
    munhak_rows_data = cache.get("munhak_quiz_rows_data")

    munhak_rows = copy.deepcopy(munhak_rows_data)
    data = {
        "total_munhak": len(munhak_rows),
        "source_list": sorted(set([munhak_row["source"] for munhak_row in munhak_rows]))
    }
    print(data)

    session["quiz_count"] = 0
    return render_template("quiz/index.html", data=data)


@quiz_bp.route('/get-quiz', methods=["GET", "POST"])
def get_quiz():
    munhak_rows_data = cache.get("munhak_quiz_rows_data")

    if "is_end" in session and session["is_end"] is True:
        session["quiz_count"] = 0
        session["total_munhak"] = len(munhak_rows_data)
        session["solved_quiz"] = []
        session["current_munhak"] = None
        session["is_end"] = False

    if "quiz_count" not in session:
        session["quiz_count"] = 0
        session["total_munhak"] = len(munhak_rows_data)
    if "solved_quiz" not in session:
        session["solved_quiz"] = []
    session["result"] = None

    quiz_no = session["quiz_count"] + 1
    solved_quiz = session["solved_quiz"]

    if "_id" not in session:
        session["_id"] = uuid.uuid4()

    if "current_munhak" not in session or session["current_munhak"] is None:

        # munhak_rows = Munhak.query.filter_by(is_available=True).all()

        munhak_rows = copy.deepcopy(munhak_rows_data)

        not_solved_munhak_rows = [munhak_row for munhak_row in munhak_rows if
                                  munhak_row["munhak_seq"] not in solved_quiz]

        if len(not_solved_munhak_rows) == 0:  # 다 맞았을 때
            session["result"] = True
            return "wow", 404

        correct_munhak_row = random.choice(not_solved_munhak_rows)

        for _ in [munhak_row for munhak_row in munhak_rows if munhak_row["title"] == correct_munhak_row["title"]]:
            munhak_rows.remove(_)  # 제목이 같은 건 선지에 넣지 않는다

        random.shuffle(munhak_rows)

        if correct_munhak_row["category"] != "극" and correct_munhak_row["category"] != "수필" and random.random() >= 0.5:
            option_munhak_rows = [munhak_row for munhak_row in munhak_rows if
                                  munhak_row["category"] == correct_munhak_row["category"]][0:3] + [correct_munhak_row]
        else:
            option_munhak_rows = munhak_rows[0:3] + [correct_munhak_row]

        random.shuffle(option_munhak_rows)
        correct = option_munhak_rows.index(correct_munhak_row)

        session["correct"] = simpleEnDecrypt.encrypt(f"{correct}:{uuid.uuid4()}")

        hint = random.choice(correct_munhak_row["keywords"])
        hint = hint.replace("\\", "")

        session["current_munhak"] = {
            "munhak_seq": correct_munhak_row["munhak_seq"],
            "source": correct_munhak_row["source"],
            "category": correct_munhak_row["category"],
            "hint": hint,
            "title": correct_munhak_row["title"],
            "writer": correct_munhak_row["writer"]
        }
        session["options"] = [munhak_row for munhak_row in option_munhak_rows]
        data = {
            "quiz_no": quiz_no,
            "type": "객관식",
            "category": correct_munhak_row["category"],
            "hint": hint,
            "options": [
                f"{munhak_row['writer']}, 『{munhak_row['title']}』" for munhak_row in option_munhak_rows
            ],
            "total_munhak": len(munhak_rows_data)
        }
        print(data)
        #
        return render_template("quiz/quiz.html", data=data)
    else:
        # print(hint)
        data = {
            "quiz_no": quiz_no,
            "type": "객관식",
            "category": session["current_munhak"]["category"],
            "hint": session["current_munhak"]["hint"],
            "options": [
                f"{munhak_row['writer']}, 『{munhak_row['title']}』" for munhak_row in session["options"]
            ],
            "total_munhak": len(munhak_rows_data)
        }
        print(data)
        #
        return render_template("quiz/quiz.html", data=data)

@quiz_bp.route('/play')
def quiz():
   return render_template("quiz/quiz_container.html")


@quiz_bp.route("/answer", methods=["GET", "POST"])
def answer():



    print(session)
    option = request.form.get("option", None)
    if option is None or (not type(option) != int):
        return abort(400)
    option = int(option)

    try:

        correct = int(simpleEnDecrypt.decrypt(session["correct"]).split(":")[0])
    except:
        return abort(401)

    if correct is None:
        return abort(401)

    current_munhak = session["current_munhak"]
    if current_munhak is None:
        return abort(401)

    if correct == option:
        session["quiz_count"] += 1
        session["solved_quiz"].append(current_munhak["munhak_seq"])
        session["current_munhak"] = None
        # current_munhak = jsonify(current_munhak)
        return get_quiz()
    else:

        if "quiz_count" not in session:
            session["quiz_count"] = 0
        if "solved_quiz" not in session:
            # session["solved_quiz"] = []
            session["result"] = False

        return "failed", 404


@quiz_bp.route("/result", methods=["GET", "POST"])
def result():
    if "result" not in session:
        return redirect(url_for("quiz.index"))

    if "quiz_count" in session and session["quiz_count"] >= 10:
        send_discord_alert_log(f"{session['quiz_count']}개를 맞혔어요!")

    is_success = session["result"]
    session["is_end"] = True

    # session["quiz_count"] = 0
    # session["solved_quiz"] = []
    # session["current_munhak"] = None

    is_best_record = False

    if "user" in session:
        user_seq = session["user"]["user_seq"]
        old_record_row = QuizRanking.query.filter_by(user_seq=user_seq).first()
        if old_record_row is None:
            if session["quiz_count"] >= 1:
                record_row = QuizRanking(user_seq=user_seq, score=session["quiz_count"], record_date=datetime.now())
                db.session.add(record_row)
                db.session.commit()
                is_best_record = True
        else:
            if session["quiz_count"] >= 1 and session["quiz_count"] > old_record_row.score:
                old_record_row.score = session["quiz_count"]
                db.session.commit()
                is_best_record = True



    data = {
        "is_success": is_success,
        "solved_count": session["quiz_count"],
        "correct": int(simpleEnDecrypt.decrypt(session["correct"]).split(":")[0]),
        "current_munhak": session["current_munhak"],
        "is_best_record": is_best_record
    }

    print(data)
    return render_template("quiz/result.html", data=data)


@quiz_bp.route("/render-ranking", methods=["GET", "POST"])
def render_ranking():
    record_rows = QuizRanking.query.order_by(desc(QuizRanking.score), asc(QuizRanking.record_date)).all()
    print(record_rows)

    if "user" in session:
        user_seq = session["user"]["user_seq"]
    else:
        user_seq = -1

    my_row = None
    for i, record_row in enumerate(record_rows):
        if record_row.user.user_seq == user_seq:
            my_row = {
                "no": i + 1,
                "nickname": record_row.user.nickname,
                "score": record_row.score
            }

    data = {
        "record_rows": [{
            "nickname": record_row.user.nickname,
            "score": record_row.score
        } for record_row in record_rows[:min(len(record_rows), 10)]],
        "my_row": my_row

    }
    return render_template("quiz/render_ranking.html", data=data)

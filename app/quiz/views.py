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
from datetime import datetime
from flask_socketio import SocketIO
from flask_socketio import emit, join_room, leave_room, rooms

from app.socket import socketio

quiz_bp = Blueprint('quiz', __name__)


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
    # import time
    # time.sleep(1)
    if "quiz_source" not in session:
        session["quiz_source"] = "all"

    quiz_source = session["quiz_source"]
    munhak_rows_data = copy.deepcopy(cache.get("munhak_quiz_rows_data"))

    if quiz_source == "s1":
        munhak_rows_data = [munhak_row for munhak_row in munhak_rows_data if
                            munhak_row["source"].split()[-1] != "수능특강" and munhak_row["source"].split()[-1] != "수능완성"]
    elif quiz_source == "s2":
        munhak_rows_data = [munhak_row for munhak_row in munhak_rows_data if
                            munhak_row["source"].split()[-1] == "수능특강" or munhak_row["source"].split()[-1] == "수능완성"]

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

        if correct_munhak_row["category"] != "극" and correct_munhak_row[
            "category"] != "수필" and random.random() >= 0.5:  # 50% 확률
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
            # "title": correct_munhak_row["title"],
            # "writer": correct_munhak_row["writer"]
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
    args = request.args
    re = "re" in args and args["re"] == "true"
    s1 = "s1" in args and args["s1"] == "false"
    s2 = "s2" in args and args["s2"] == "false"
    if re:
        if s1 and not s2:
            session["quiz_source"] = "s2"
        elif not s1 and s2:
            session["quiz_source"] = "s1"
        else:
            session["quiz_source"] = "all"

        session["quiz_count"] = 0
        session["solved_quiz"] = []
        session["current_munhak"] = None
        session["is_end"] = False
        return redirect(url_for("quiz.quiz"))

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

    correct = int(simpleEnDecrypt.decrypt(session["correct"]).split(":")[0])
    data = {
        "is_success": is_success,
        "solved_count": session["quiz_count"],
        "correct": correct,
        "current_munhak": session["current_munhak"],
        "is_best_record": is_best_record,
        "correct_option": session["options"][correct]
    }
    print(session["options"][correct])

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


######################################################################

room_info = {}


@quiz_bp.route('/live')
def enter_live():
    return render_template("./quiz/live/index.html")


@quiz_bp.route('/live/make-room')
def make_room():
    global room_info
    # room_info = cache.get("room_info")
    args = request.args
    if "nickname" in args:
        if 1 <= len(args["nickname"]) <= 20:
            session["live_nickname"] = args["nickname"]
        else:

            return redirect(url_for("quiz.enter_live"))
    else:

        return redirect(url_for("quiz.enter_live"))

    random_num = -1
    while random_num == -1:
        print(random_num)
        random_num = random.randint(100000, 999999)
        if random_num in room_info.keys():
            random_num = -1
            continue
        room_info[random_num] = {
            "users": {},
            "room_master": None,
            "is_playing": False,
            "quiz_data_list": [],
            "setting" : {
                "correct_score" : 2,
                "wrong_score" : -1,
                "goal_score" : 20
            },
            "game_code" : "",
        }

    print("room_info", room_info)

    # cache.set("room_info", room_info)

    return redirect(url_for("quiz.live_room", room_id=random_num))


@quiz_bp.route('/live/enter-room')
def enter_room():
    global room_info
    # room_info = cache.get("room_info")
    args = request.args
    if "nickname" in args:
        if 1 <= len(args["nickname"]) <= 20:
            session["live_nickname"] = args["nickname"]
        else:
            return redirect(url_for("quiz.enter_live"))
    else:
        return redirect(url_for("quiz.enter_live"))

    if "room_id" in args:

        if not args["room_id"].isdigit():
            return redirect(url_for("quiz.enter_live"))

        if int(args["room_id"]) in room_info:
            return redirect(url_for("quiz.live_room", room_id=int(args["room_id"])))
        else:
            return redirect(url_for("quiz.enter_live"))
    else:
        return redirect(url_for("quiz.enter_live"))


@quiz_bp.route('/live/<int:room_id>')
def live_room(room_id):
    global room_info
    # room_info = cache.get("room_info")
    print("room_info", room_info, room_id)

    if room_id not in room_info or room_info[room_id]["is_playing"] is True:
        return redirect(url_for("quiz.enter_live"))

    return render_template("./quiz/live/room.html", data={"room_id": room_id})


def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')


@socketio.on('connect', namespace="/live")
def on_connect():
    print("connect")


@socketio.on('disconnect')
def on_disconnect():
    leave_live_room(request.sid)

    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$4")


@socketio.on('leave_live_room', namespace="/live")
def leave_live_room(target_sid=None):
    global room_info
    # room_info = cache.get("room_info")
    if target_sid is None:
        target_sid = request.sid

    for room in room_info:
        for sid in list(room_info[room]["users"]):
            if sid == target_sid:
                del room_info[room]["users"][sid]
                room_id = room

                leave_room(room_id, sid=sid, namespace="/live")

                if len(room_info[room_id]["users"]) == 0:
                    del room_info[room_id]
                else:

                    if sid == room_info[room_id]["room_master"]:
                        room_info[room_id]["room_master"] = list(room_info[room_id]["users"])[0]

                    emit("update_room_info", {
                        "users": room_info[room_id]["users"],
                        "room_master": room_info[room_id]["room_master"],
                        "setting": room_info[room_id]["setting"]
                    }, room=room_id, namespace="/live")

    cache.set("room_info", room_info)


@socketio.on('join_live_room', namespace="/live")
def join_live_room(data, methods=['GET', 'POST']):
    color_list = [
        "red", "green", "blue", "orange", "pink", "yellow"
    ]

    global room_info
    # room_info = cache.get("room_info")

    if "live_nickname" not in session:
        emit("error")
        return

    print(request.sid)
    room_id = data["room_id"]
    # if "uid" not in session:
    #     session["uid"] = uuid.uuid4()
    # if "live_nickname" not in session:
    #     return redirect(url_for("quiz.enter_live"))
    print(room_id)
    if room_id not in room_info:
        emit("error")

        return

    join_room(room=room_id)
    # print(rooms(sid=session["uid"], namespace="/live"))

    for room in room_info:
        for sid in room_info[room]["users"].keys():
            if sid == request.sid:
                del room_info[room]["users"][sid]

    if room_info[room_id]["room_master"] is None:
        room_info[room_id]["room_master"] = request.sid

    print(room_info)

    exist_color_list = [v["color"] for k, v in room_info[room_id]["users"].items()]
    available_color_list = list(set(color_list) - set(exist_color_list))
    random.shuffle(available_color_list)

    room_info[room_id]["users"][request.sid] = {
        "nickname": session["live_nickname"],
        "color": available_color_list[0],
        "is_ready": False,
    }
    print(room_info)

    emit("update_room_info", {
        "users": room_info[room_id]["users"],
        "room_master": room_info[room_id]["room_master"],
        "setting": room_info[room_id]["setting"]
    }, room=room_id, namespace="/live")
    # cache.set("room_info", room_info)

    # print('received my event: ' + str(json)/)
    # socketio.emit('my response', data[", callback=messageReceived)


@socketio.on("ready_live", namespace="/live")
def ready_live(data):
    global room_info

    room_id = data["room_id"]
    if room_id not in room_info or room_info[room_id]["room_master"] == request.sid or room_info[room_id][
        "is_playing"] is not False:
        return

    room_info[room_id]["users"][request.sid]["is_ready"] = not room_info[room_id]["users"][request.sid]["is_ready"]

    emit("update_room_info", {
        "users": room_info[room_id]["users"],
        "room_master": room_info[room_id]["room_master"],
        "setting": room_info[room_id]["setting"]
    }, room=room_id, namespace="/live")


@socketio.on('start_live', namespace="/live")
def start_live(data):
    global room_info
    # room_info = cache.get("room_info")
    room_id = data["room_id"]
    if room_id not in room_info or room_info[room_id]["room_master"] != request.sid or room_info[room_id][
        "is_playing"] is not False:
        emit("error")

    for sid in room_info[room_id]["users"]:
        if sid != request.sid and room_info[room_id]["users"][sid]["is_ready"] != True:
            emit("alert_message", "모두 준비하지 않았습니다")
            return

    munhak_rows_data = cache.get("munhak_quiz_rows_data")

    room_info[room_id]["is_playing"] = True

    selected_quiz_list = []
    quiz_data_list = []
    munhak_rows = copy.deepcopy(munhak_rows_data)
    for quiz_no in range(1, len(munhak_rows)):

        not_selected_munhak_rows = [munhak_row for munhak_row in munhak_rows if
                                    munhak_row["munhak_seq"] not in selected_quiz_list]
        # print(quiz_no)
        # print(not_selected_munhak_rows)
        # print(selected_quiz_list)

        if not not_selected_munhak_rows:
            break

        correct_munhak_row = random.choice(not_selected_munhak_rows)

        for _ in [munhak_row for munhak_row in munhak_rows if munhak_row["title"] == correct_munhak_row["title"]]:
            munhak_rows.remove(_)  # 제목이 같은 건 선지에 넣지 않는다

        random.shuffle(munhak_rows)

        if correct_munhak_row["category"] != "극" and correct_munhak_row[
            "category"] != "수필" and random.random() >= 0.5:  # 50% 확률
            option_munhak_rows = [munhak_row for munhak_row in munhak_rows if
                                  munhak_row["category"] == correct_munhak_row["category"]][0:3] + [correct_munhak_row]
        else:
            option_munhak_rows = munhak_rows[0:3] + [correct_munhak_row]

        random.shuffle(option_munhak_rows)
        correct = option_munhak_rows.index(correct_munhak_row)

        hint = random.choice(correct_munhak_row["keywords"])
        hint = hint.replace("\\", "")

        quiz_data = {
            "quiz_no": quiz_no,
            "munhak_seq": correct_munhak_row["munhak_seq"],
            "source": correct_munhak_row["source"],
            "category": correct_munhak_row["category"],
            "hint": hint,
            "correct": correct,
            "options": [
                f"{munhak_row['writer']}, 『{munhak_row['title']}』" for munhak_row in option_munhak_rows
            ],
            "title": correct_munhak_row["title"],
            "writer": correct_munhak_row["writer"]
        }

        selected_quiz_list.append(correct_munhak_row["munhak_seq"])
        quiz_data_list.append(quiz_data)

    print(quiz_data_list)

    room_info[room_id]["quiz_data_list"] = quiz_data_list

    for sid in room_info[room_id]["users"]:
        room_info[room_id]["users"][sid]["quiz_no"] = 1
        room_info[room_id]["users"][sid]["correct"] = 0
        room_info[room_id]["users"][sid]["wrong"] = 0
        room_info[room_id]["users"][sid]["score"] = 0

    game_code = uuid.uuid4()
    room_info[room_id]["game_code" ] = game_code


    emit("live_started", {
        "users": room_info[room_id]["users"],
        "goal_score": room_info[room_id]["setting"]["goal_score"],
        "correct_score": room_info[room_id]["setting"]["correct_score"],
        "wrong_score": room_info[room_id]["setting"]["wrong_score"]
    }, room=room_id)

    import time
    time.sleep(93)
    if  room_info[room_id]["game_code" ] == game_code:
        end_live(room_id)


    # cache.set("room_info", room_info)


def end_live(room_id):
    try:
        user_list = copy.deepcopy(room_info[room_id]["users"])
    except:
        return

    user_list = {k: v for k, v in sorted(user_list.items(), key=lambda item: item[1]["score"], reverse=True)}

    room_info[room_id]["is_playing"] = False

    for sid in room_info[room_id]["users"]:
        room_info[room_id]["users"][sid]["is_ready"] = False

    emit("end_live", {
        "users": user_list
    }, room=room_id)

    emit("update_room_info", {
        "users": room_info[room_id]["users"],
        "room_master": room_info[room_id]["room_master"],
        "setting": room_info[room_id]["setting"]
    }, room=room_id, namespace="/live")



@socketio.on('mark_and_get_quiz', namespace="/live")
def mark_and_get_quiz(data):
    import time
    # time.sleep(1)

    if data["room_id"] not in room_info:
        return
    is_correct = None
    sid = request.sid
    room_id = data["room_id"]
    quiz_no = room_info[room_id]["users"][sid]["quiz_no"]

    CORRECT_SCORE = room_info[room_id]["setting"]["correct_score"]
    WRONG_SCORE = room_info[room_id]["setting"]["wrong_score"]
    GOAL_SCORE = room_info[room_id]["setting"]["goal_score"]


    if "answer" in data:
        quiz = room_info[room_id]["quiz_data_list"][quiz_no - 1]
        print(quiz)
        if quiz["correct"] == data["answer"]:
            is_correct = True
            if room_info[room_id]["users"][sid]["score"] + CORRECT_SCORE <= GOAL_SCORE:
                room_info[room_id]["users"][sid]["score"] = room_info[room_id]["users"][sid]["score"] + CORRECT_SCORE
            else:
                room_info[room_id]["users"][sid]["score"] = GOAL_SCORE
        else:
            is_correct = False

            if room_info[room_id]["users"][sid]["score"] + WRONG_SCORE >= 0:
                room_info[room_id]["users"][sid]["score"] = room_info[room_id]["users"][sid]["score"] + WRONG_SCORE
            else:
                room_info[room_id]["users"][sid]["score"] = 0

        emit("solve_progress", {
            "sid": request.sid,
            "score": room_info[room_id]["users"][sid]["score"]
        }, room=room_id)

        if room_info[room_id]["setting"]["goal_score"] <= room_info[room_id]["users"][sid]["score"]:
            end_live(room_id)

            return

        quiz_no += 1
        room_info[room_id]["users"][sid]["quiz_no"] = room_info[room_id]["users"][sid]["quiz_no"] + 1

    print(quiz_no)

    # next quiz

    try:
        quiz_data_temp = room_info[room_id]["quiz_data_list"][quiz_no - 1]
        quiz_data = {
            "quiz_no": quiz_no,
            "munhak_seq": quiz_data_temp["munhak_seq"],
            "source": quiz_data_temp["source"],
            "category": quiz_data_temp["category"],
            "hint": quiz_data_temp["hint"],
            "options": quiz_data_temp["options"],
        }

        emit("receive_quiz", {
            "quiz_data": quiz_data, "is_correct": is_correct
        })
    except:
        emit("receive_quiz", {
            "quiz_data": None,  "is_correct": is_correct
        })

@socketio.on('edit_room_setting', namespace="/live")
def edit_room_setting(data):
    global room_info
    # room_info = cache.get("room_info")
    room_id = data["room_id"]
    print(data)

    if room_id not in room_info or room_info[room_id]["room_master"] != request.sid or room_info[room_id][
        "is_playing"] is not False:
        emit("error")


    if data["goal_score"] // 1 >= 1:
        room_info[room_id]["setting"]["goal_score"] = min(int(data["goal_score"] // 1), 1000)
    if data["correct_score"] // 1 >= 1:
        room_info[room_id]["setting"]["correct_score"] = int(data["correct_score"] // 1)
    if data["wrong_score"] // 1 >= 0:
        room_info[room_id]["setting"]["wrong_score"] = int(data["wrong_score"] // 1) * -1

    emit("room_setting_edited", room_info[room_id]["setting"], room=room_id, namespace="/live")
    # cache.set("room_info", room_info)

import configparser

from flask import Flask, render_template, session, request, flash, redirect, url_for, Response, abort, jsonify
import socket
import os
import random
import copy
from flask_sqlalchemy import SQLAlchemy, Model
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import base64
from collections import namedtuple
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

hostname = socket.gethostname()
isLocal = None

munhak_rows_data = None

if hostname[:7] == "DESKTOP":
    isLocal = True
else:
    isLocal = False

app = Flask(__name__)


def update():

        gc = gspread.authorize(credentials).open("문학따먹기")

        wks = gc.get_worksheet(0)

        rows = wks.get_all_values()
        print(rows)
        try:

            data = []
            for row in rows[1:]:
                row_tuple = namedtuple("Munhak", rows[0])(*row)
                row_tuple = row_tuple._replace(keywords=json.loads(row_tuple.keywords))
                if row_tuple.is_available == "TRUE":
                    data.append(row_tuple)


        except:
            pass

        global munhak_rows_data
        munhak_rows_data = data
        print(data)
        # print(munhak_rows)
        return



if isLocal:
    config = configparser.ConfigParser()
    config.read('config.ini')

    pg_db_username = config['DEFAULT']['LOCAL_DB_USERNAME']
    pg_db_password = config['DEFAULT']['LOCAL_DB_PASSWORD']
    pg_db_name = config['DEFAULT']['LOCAL_DB_NAME']
    pg_db_hostname = config['DEFAULT']['LOCAL_DB_HOSTNAME']

    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://{DB_USER}:{DB_PASS}@{DB_ADDR}/{DB_NAME}".format(
        DB_USER=pg_db_username,
        DB_PASS=pg_db_password,
        DB_ADDR=pg_db_hostname,
        DB_NAME=pg_db_name)

    app.config["SECRET_KEY"] = config['DEFAULT']['SECRET_KEY']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(config['DEFAULT']['GOOGLE_CREDENTIALS_PATH'], scope)
    update()
else:

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL', None)
    app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', None)
    print(os.environ.get('GOOGLE_CREDENTIALS', None))
    print(json.loads(os.environ.get('GOOGLE_CREDENTIALS', None)))
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(os.environ.get('GOOGLE_CREDENTIALS', None)), scope)

    update()





# class CustomModel(Model):
#     def as_dict(self):
#         temp = {}
#         for x in self.__table__.columns:
#             if str(type(getattr(self, x.name))) == "<class 'datetime.datetime'>":
#                 temp[x.name] = str(getattr(self, x.name))
#             else:
#                 temp[x.name] = getattr(self, x.name)
#         return temp
#
#
# db = SQLAlchemy(app, model_class=CustomModel)
#
#
# class Munhak(db.Model):
#     __table_args__ = {'mysql_collate': 'utf8_general_ci'}
#
#     munhak_seq = db.Column(db.Integer, primary_key=True, nullable=False)
#
#     category = db.Column(db.String(20), nullable=True)
#     source = db.Column(db.String(50), nullable=True)
#
#     title = db.Column(db.String(100), nullable=False)
#     writer = db.Column(db.String(50), nullable=True)
#     keywords = db.Column(db.JSON, nullable=True)
#
#     is_available = db.Column(db.Boolean, nullable=False)


@app.route('/')
def index():
    session["quiz_count"] = 0
    return render_template("index.html")


@app.route('/quiz')
def quiz():
    if "quiz_count" not in session:
        session["quiz_count"] = 0
    if "solved_quiz" not in session:
        session["solved_quiz"] = []
    session["result"] = None

    quiz_no = session["quiz_count"] + 1
    solved_quiz = session["solved_quiz"]

    if "current_munhak" not in session or session["current_munhak"] is None:

        # munhak_rows = Munhak.query.filter_by(is_available=True).all()
        munhak_rows = copy.deepcopy(munhak_rows_data)


        not_solved_munhak_rows = [munhak_row for munhak_row in munhak_rows if munhak_row.munhak_seq not in solved_quiz]

        if len(not_solved_munhak_rows) == 0:
            session["result"] = True
            return redirect(url_for("result"))


        correct_munhak_row = random.choice(not_solved_munhak_rows)
        munhak_rows.remove(correct_munhak_row)

        random.shuffle(munhak_rows)

        option_munhak_rows = munhak_rows[0:3] + [correct_munhak_row]

        random.shuffle(option_munhak_rows)
        correct = option_munhak_rows.index(correct_munhak_row)
        print(correct)

        # correct = random.randrange(0, 4)
        #
        # answer_row = not_solved_munhak_rows[correct]
        #
        session["correct"] = correct

        hint = random.choice(correct_munhak_row.keywords)
        hint = hint.replace("\\", "")

        session["current_munhak"] = {
            "munhak_seq" : correct_munhak_row.munhak_seq,
            "source" : correct_munhak_row.source,
            "category" : correct_munhak_row.category,
            "hint" : hint,
            "title" : correct_munhak_row.title,
            "writer" : correct_munhak_row.writer
        }
        session["options"] = [munhak_row._asdict() for munhak_row in option_munhak_rows]
        data = {
            "quiz_no": quiz_no,
            "type": "객관식",
            "category": correct_munhak_row.category,
            "hint": hint,
            "options": [
                f"{munhak_row.writer}, 『{munhak_row.title}』" for munhak_row in option_munhak_rows
            ]
        }
        print(data)
        #
        return render_template("quiz.html", data=data)
    else:
        # print(hint)
        data = {
            "quiz_no": quiz_no,
            "type": "객관식",
            "category": session["current_munhak"]["category"],
            "hint": session["current_munhak"]["hint"],
            "options": [
                f"{munhak_row['writer']}, 『{munhak_row['title']}』" for munhak_row in session["options"]
            ]
        }
        print(data)
        #
        return render_template("quiz.html", data=data)

@app.route("/answer", methods=["GET", "POST"])
def answer():
    print(session)
    option = request.form.get("option", None)
    if option is None or (not type(option) != int):
        return abort(400)
    option = int(option)
    correct = session["correct"]
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
        return "success"
    else:

        if "quiz_count" not in session:
            session["quiz_count"] = 0
        if "solved_quiz" not in session:
            # session["solved_quiz"] = []
            session["result"] = False

        return "failed", 404



@app.route("/result", methods=["GET", "POST"])
def result():


    is_success = session["result"]


    data = {
        "is_success" : is_success,
        "solved_count" : session["quiz_count"],
        "correct" : session["correct"],
        "current_munhak" : session["current_munhak"]
    }
    session["quiz_count"] = 0
    session["solved_quiz"] = []
    session["current_munhak"] = None

    print(data)
    return render_template("result.html", data = data)


@app.route('/update')

def update_():

    if request.args.get("key", None) != app.config["SECRET_KEY"]:
        return "error"

    update()




if __name__ == '__main__':

    app.run()

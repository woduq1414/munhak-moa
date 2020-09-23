import configparser

from flask import Flask, render_template, session, request, flash, redirect, url_for, Response, abort, jsonify
import socket
import os
import random

from flask_sqlalchemy import SQLAlchemy, Model

hostname = socket.gethostname()
isLocal = None
if hostname[:7] == "DESKTOP":
    isLocal = True
else:
    isLocal = False

app = Flask(__name__)

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
else:

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL', None)
    app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', None)


class CustomModel(Model):
    def as_dict(self):
        temp = {}
        for x in self.__table__.columns:
            if str(type(getattr(self, x.name))) == "<class 'datetime.datetime'>":
                temp[x.name] = str(getattr(self, x.name))
            else:
                temp[x.name] = getattr(self, x.name)
        return temp


db = SQLAlchemy(app, model_class=CustomModel)


class Munhak(db.Model):
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}

    munhak_seq = db.Column(db.Integer, primary_key=True, nullable=False)

    category = db.Column(db.String(20), nullable=True)
    source = db.Column(db.String(50), nullable=True)

    title = db.Column(db.String(100), nullable=False)
    writer = db.Column(db.String(50), nullable=True)
    keywords = db.Column(db.JSON, nullable=True)

    is_available = db.Column(db.Boolean, nullable=False)


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

        munhak_rows = Munhak.query.filter_by(is_available=True).all()

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
        session["current_munhak"] = {
            "munhak_seq" : correct_munhak_row.munhak_seq,
            "source" : correct_munhak_row.source,
            "category" : correct_munhak_row.category,
            "hint" : hint,
            "title" : correct_munhak_row.title,
            "writer" : correct_munhak_row.writer
        }
        session["options"] = [munhak_row.as_dict() for munhak_row in option_munhak_rows]
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
    print(data)
    return render_template("result.html", data = data)


if __name__ == '__main__':
    app.run()

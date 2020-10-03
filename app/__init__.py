import os

from flask import Flask, Response
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from app.common.function import *
import json
from flaskext.markdown import Markdown


class MyResponse(Response):
    default_mimetype = 'application/xml'


from flask import request, Response
from werkzeug.exceptions import HTTPException


# import flask_admin.contrib.sqla


# http://flask.pocoo.org/docs/0.10/patterns/appfactories/
def create_app(config_filename):
    app = Flask(__name__, static_url_path='', static_folder='../static', template_folder='../templates')

    app.config.from_object(config_filename)
    # app.response_class = MyResponse

    from app.db import db
    db.init_app(app)
    db.app = app
    # sched.init_app(app)
    # redis_client.init_app(app)

    from app.cache import cache
    # Blueprints
    from app.quiz.views import quiz_bp
    from app.others.views import others_bp
    from app.board.views import board_bp
    from app.user.views import user_bp
    # from app.students.views import users_bp
    # from app.schools.views import schools_bp
    # from app.meals.views import meals_bp
    # from app.board.views import board_bp
    #
    #
    app.register_blueprint(quiz_bp, url_prefix='/quiz')
    app.register_blueprint(others_bp, url_prefix='/')
    app.register_blueprint(board_bp, url_prefix='/')
    app.register_blueprint(user_bp, url_prefix='/')
    # app.register_blueprint(users_bp, url_prefix='/api/students')
    # app.register_blueprint(schools_bp, url_prefix='/api/schools')
    # app.register_blueprint(meals_bp, url_prefix='/api/meals')
    # app.register_blueprint(board_bp, url_prefix='/api/board')

    # sched.add_job(lambda: update_meal_board_views(), 'cron', second='05', id="update_meal_board_views")
    Markdown(app, extensions=['nl2br', 'fenced_code'])

    fetch_spread_sheet()

    app.add_template_global(name="TAG_SOURCE",
                            f=list(
                                {"건국신화", "고대가요", "설화", "향가", "4구체", "8구체", "한시", "전", "소악부", "시조", "한시", "고려속요", "가전체",
                                 "한문소설", "악장", "경기체가", "가사", "몽유록", "고대", "중세", "근대", "사대부", "국문", "사설시조", "국문소설", "야담",
                                 "구비문학", "신소설", "근대소설", "잡가", "사실주의", "계급주의", "낭만주의", "서사시", "모더니즘", "농촌소설", "역사소설",
                                 "순수소설", "순수시", "생명파", "전원파", "민요", "창가", "신체시", "자유시", "저항시", "청록파", "일제강점기", "전후소설",
                                 "사실주의", "참여시", "민중시", "포스트모더니즘"
                                                       "반어법", "역설법", "수미상관", "서정시", "극시", "서경시", "정형시", "자유시", "산문시",
                                 "판소리", "마당극", "인형극", "패관문학", }))

    CORS(app)
    return app

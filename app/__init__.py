
import os


from flask import Flask, Response
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from app.common.function import *
import json




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


    fetch_spread_sheet()


    CORS(app)
    return app

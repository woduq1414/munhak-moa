#!/usr/bin/env python
from app import create_app

from app.socket import socketio

from flask import render_template, redirect, url_for
# app = create_app('config')
# app.app_context().push()
from app.common.decorator import return_500_if_errors
from app.db import db

from functools import wraps
from flask import request, Response, g, jsonify
from config import SECRET_KEY
from app.common.function import *

import traceback
import requests
from datetime import datetime
import threading
import socket
import os
from flask_socketio import SocketIO


app = create_app('config')


# db.create_all(app=app)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.close()


# routing > react_router (method = GET)
@app.route('/', defaults={'path': ''}, methods=['GET'])
# @app.route('/<string:path>', methods=['GET'])
def catch_all(path):
    return render_template('index.html')


# 404 not found > react_router
# @app.errorhandler(404)
# def not_found(error):
#     return redirect(url_for("others.index"))


@app.errorhandler(500)
def error_handler(e):

    print(traceback.print_exc())
    if is_local():
        return jsonify({
            "message": "error"
        }), 500


    error_message = traceback.format_exc()
    ip_address = request.headers[
        'X-Forwarded-For'] if 'X-Forwarded-For' in request.headers else request.remote_addr
    print(json.dumps(request.get_json()) or "null")
    webhook_body = {

        "embeds": [
            {
                "title": "=========ERROR=========",
                "color": 14177041

            },
            {
                "fields": [
                    {
                        "name": "URI",
                        "value": request.url,
                        "inline": True
                    },
                    {
                        "name": "Request Args",
                        "value": json.dumps(request.args) or "null"
                    },
                    {
                        "name": "Request Form",
                        "value": json.dumps(request.form) or "null"
                    },

                ],
                "color": 0

            },
            {
                "description": error_message,
                "color": 14177041
            },
            {
                "title": str(datetime.now()) + ", " + (
                    "로컬에서 발생" if is_local() else "외부에서 발생") + ", " + ip_address,
                "color": 0
            },

        ]
    }
    threading.Thread(target=lambda: send_discord_webhook(webhook_body=webhook_body)).start()

    response = {
        "message": "error"
    }

    return jsonify(response), 500


if __name__ == '__main__':
    socketio.run(app, debug=True)
    # app.run(host=app.config['HOST'],
    #         port=app.config['PORT'],
    #         debug=app.config['DEBUG'])
# print(app.config["DEBUG"])
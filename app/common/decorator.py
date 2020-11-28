from functools import wraps
from flask import request, Response, g, jsonify, session, abort
def login_required(f):  # 1)
    @wraps(f)  # 2)
    def decorated_function(*args, **kwargs):

        if "user" in session:

            pass
        else:
            return abort(401)  # 9)

        return f(*args, **kwargs)

    return decorated_function









import jwt

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


def return_500_if_errors(f):
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print("no!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!11")
            print(traceback.print_exc())
            if is_local() and False:
                return jsonify({
                           "message": "error"
                       }), 500

            print(f)
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
                                "name": "Function",
                                "value": str(f),
                                "inline": True
                            },
                            {
                                "name": "URI",
                                "value": request.url,
                                "inline": True
                            },
                            {
                                "name": "Request Body",
                                "value": json.dumps(request.args) or json.dumps(requests.form) or "null"
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

    return wrapper


def set_user_theme(f):
    def wrapper(*args, **kwargs):
        print(request.cookies)

    return wrapper
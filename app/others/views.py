
from flask import Blueprint
from flask import Flask, render_template, session, request, flash, redirect, url_for, Response, abort, jsonify, send_file
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

from config import credentials, SECRET_KEY
from app.cache import cache
from app.common.function import fetch_spread_sheet

others_bp = Blueprint('others', __name__)


@others_bp.route('/update')

def update_():

    if request.args.get("key", None) != others_bp.config["SECRET_KEY"]:
        return "error"

    len_data = fetch_spread_sheet()
    session.clear()
    return f"success! {len(len_data)}"


@others_bp.route('/images/<path:path>')
def get_image(path):
    def get_absolute_path(path):
        import os
        script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in
        rel_path = path
        abs_file_path = os.path.join(script_dir, rel_path)
        return abs_file_path

    return send_file(
        get_absolute_path(f"../../images/{path}"),
        mimetype='image/png',
        attachment_filename='snapshot.png',
        cache_timeout=0
    )
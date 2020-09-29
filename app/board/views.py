from flask import Blueprint, make_response
from flask import Flask, render_template, session, request, flash, redirect, url_for, Response, abort, jsonify, \
    send_file
import socket
import base64
import os
import random
import copy
from sqlalchemy import func, desc
# from app.global_var import munhak_rows_data
from flask_sqlalchemy import SQLAlchemy, Model
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import base64
from collections import namedtuple, defaultdict
from flask_restful import Api, Resource, reqparse
import re
from app.common.decorator import login_required
from config import credentials, SECRET_KEY, YOUTUBE_KEY
from app.cache import cache
from app.common.function import *
import requests
from app.db import *

from datetime import datetime
from itertools import groupby
board_bp = Blueprint('board', __name__)


@board_bp.route('/test')
def test():
    return render_template("test.html")


@board_bp.route('/board/detail/<int:munhak_seq>/<munhak_title>/')
@board_bp.route('/board/detail/<int:munhak_seq>/', defaults={'munhak_title': None})
def munhak_board_detail(munhak_seq, munhak_title):
    munhak_rows_data = cache.get("munhak_rows_data")
    munhak_rows = copy.deepcopy(munhak_rows_data)

    target_munhak_row = None
    for munhak_row in munhak_rows:
        if munhak_row["munhak_seq"] == munhak_seq:
            target_munhak_row = munhak_row
    print(munhak_rows)
    print(target_munhak_row)
    if target_munhak_row is None:
        return render_template("munhak_board_detail_404.html")

    if munhak_title != format_url_title(target_munhak_row["title"]):
        return redirect(url_for('board.munhak_board_detail', munhak_seq=munhak_seq,
                                munhak_title=format_url_title(target_munhak_row["title"])))

    if "user" in session:
        user_seq = session["user"]["user_seq"]
    else:
        user_seq = -1

    munhak_video_rows = Video.query.filter_by(munhak_seq=target_munhak_row["munhak_seq"]).all()
    exam_video_rows = Video.query.filter_by(munhak_source=target_munhak_row["source"]).all()

    munhak_video_list = [
        dict(video_row.as_dict(), **{"is_mine": "true" if video_row.user_seq == user_seq else "false"}) for video_row
        in munhak_video_rows]
    exam_video_list = [
        dict(video_row.as_dict(), **{"is_mine": "true" if video_row.user_seq == user_seq else "false"}) for video_row
        in exam_video_rows]
    print(munhak_video_list)
    print(exam_video_list)

    tag_rows = db.session.query(Tag, func.count(Like.like_seq).label("like_count"),
                                func.count(Like.like_seq).filter(Like.user_seq == user_seq).label("liked")

                                ).outerjoin(
        Like,
        Tag.tag_seq == Like.tag_seq).filter(Tag.munhak_seq == munhak_seq).group_by(Tag.tag_seq).order_by(
        desc("like_count")).all()

    # return "DD"
    data = {
        "munhak_seq": munhak_seq,
        "title": target_munhak_row["title"],
        "writer": target_munhak_row["writer"],
        "source": target_munhak_row["source"],
        "category": target_munhak_row["category"],
        "munhak_video_list": munhak_video_list,
        "exam_video_list": exam_video_list,
        "subject": target_munhak_row["subject"],
        "tags": [dict(tag_row.Tag.as_dict(),
                      **{"like_count": tag_row.like_count, "liked": "true" if tag_row.liked == 1 else "false",
                         "is_mine": "true" if tag_row.Tag.user_seq == user_seq else "false"}) for
                 tag_row in tag_rows]
    }
    return render_template("munhak_board_detail.html", data=data)


@board_bp.route('/board/render-card')
def munhak_board_render_card():
    munhak_rows_data = cache.get("munhak_rows_data")
    munhak_rows = copy.deepcopy(munhak_rows_data)

    args = request.args
    query = args.get("q", "")
    # tags = args.get("tags", None)


    query_list = query.split()
    origin_query_list = copy.deepcopy(query_list)
    try:
        page = int(args.get("page", 1))
    except:
        page = 1
    page_size = 10
    # query_list.remove("#")
    print(query)
    print(query_list)
    query_source_list = [word[1:].replace("-", " ") for word in query_list if word[0] == "@"]
    print("qsl", query_source_list)
    query_category_list = [word[1:] for word in query_list if word[0] == "$"]
    print("qcl", query_category_list)

    query_list = [word for word in query_list if word[0] != "@" and word[0] != "$"]

    if len(query_list) != 0:
        query_munhak_seq_set = set()

        for word in query_list:

            if word[0] != "#":
                for munhak_row in munhak_rows:
                    if word in munhak_row["title"].replace(" ", "") or word == munhak_row["writer"]:
                        query_munhak_seq_set.add(munhak_row["munhak_seq"])

        print(Tag.query.filter(
            Tag.tag_name.in_([word[1:] for word in query_list if word[0] == "#"])).all())

        tag_rows = Tag.query.filter(
            Tag.tag_name.in_([word[1:] for word in query_list if word[0] == "#"])).all()

        for tag_row in tag_rows:
            query_munhak_seq_set.add(tag_row.munhak_seq)
        # query_munhak_seq_set.add()

        print(query_munhak_seq_set)

        query_munhak_rows = [
            [munhak_row for munhak_row in munhak_rows if munhak_seq == munhak_row["munhak_seq"]][0] for munhak_seq in
            query_munhak_seq_set]
        print(query_munhak_rows)

    else:
        query_munhak_rows = munhak_rows

    query_munhak_rows = [
        munhak_row for munhak_row in query_munhak_rows if munhak_row["source"] not in query_source_list and munhak_row[
            "category"] not in query_category_list]

    query_munhak_rows = sorted(query_munhak_rows, key= lambda x : (x["source"][:5], x["source"]), reverse=True)


    data = {
        "page": page,
        "max_page": (len(query_munhak_rows) - 1) // page_size + 1,
        "query": query,
        "munhak_rows": [
            {
                "munhak_seq": munhak_row["munhak_seq"],
                "title": munhak_row["title"],
                "writer": munhak_row["writer"],
                "source": munhak_row["source"],
                "category": munhak_row["category"],
                "tags": [tag_row.tag_name for tag_row in
                         db.session.query(Tag)
                             .outerjoin(Like, Tag.tag_seq == Like.tag_seq)
                             .filter(Tag.munhak_seq == munhak_row["munhak_seq"])
                             .group_by(Tag.tag_seq)
                             .order_by(desc(func.count(Like.like_seq).label("like_count")))
                             .all()
                         ][:5],

            } for munhak_row in query_munhak_rows[(page - 1) * page_size:  page * page_size]
        ],
        "search_query_tags": [word[1:] for word in query_list if word[0] == "#"],
        "total_rows" : len(query_munhak_rows)
    }
    print([word[1:] for word in query_list if word[0] == "#"])
    resp = make_response(render_template("munhak_board_card.html", data=data))

    query_cookie = " ".join(origin_query_list)
    resp.set_cookie('query', base64.b64encode(query_cookie.encode("UTF-8")))
    # print( )

    return resp


@board_bp.route('/board')
def munhak_board_list():
    munhak_rows_data = cache.get("munhak_rows_data")
    munhak_rows = copy.deepcopy(munhak_rows_data)

    args = request.args
    query = args.get("query", "")
    tag = args.get("tag", None)
    clear = args.get("clear", None)

    if clear is not None:
        resp = make_response(redirect(url_for("board.munhak_board_list")))
        resp.set_cookie('query', "")
        resp.set_cookie("page", "1")
        return resp

    # print(query, tags)

    try:
        page = int(args.get("page", 1))
    except:
        page = 1
    page_size = 10

    source_list = sorted(list(set([munhak_row["source"] for munhak_row in munhak_rows])))
    source_dict = defaultdict(list)
    for source in source_list:
        source_dict[source[:5]].append(source)



    data = {
        "source_dict": source_dict
    }
    if tag is not None:
        resp = make_response(redirect(url_for("board.munhak_board_list")))
        query_cookie = "#" + tag
        resp.set_cookie('query', base64.b64encode(query_cookie.encode("UTF-8")))
        resp.set_cookie("page", str(page))

        return resp
    else:
        resp = make_response(render_template("munhak_board_list.html", data=data))
        resp.set_cookie("page", str(page))
        return resp


@board_bp.route("/tag/add", methods=["GET", "POST"])
@login_required
def add_tag():
    args = request.form
    munhak_seq = args.get("munhak_seq", None)
    tag_name = args.get("tag_name", None)
    print(args)
    if munhak_seq is None or not munhak_seq.isdigit() or tag_name is None or type(tag_name) != str:
        return abort(400)
    if not (1 <= len(tag_name) <= 10):
        return abort(400)
    munhak_seq = int(munhak_seq)

    munhak_rows_data = cache.get("munhak_rows_data")
    munhak_rows = copy.deepcopy(munhak_rows_data)
    if len([munhak_row for munhak_row in munhak_rows if munhak_row["munhak_seq"] == munhak_seq]) == 0:
        return abort(404)

    tag_name = re.sub("[^가-힣ㄱ-ㅎㅏ-ㅣa-zA-Z0-9]", "", tag_name)

    user_seq = session["user"]["user_seq"]

    old_tag_row = Tag.query.filter_by(tag_name=tag_name, munhak_seq=munhak_seq).first()
    if old_tag_row is not None:
        return abort(409)

    tag_row = Tag(
        tag_name=tag_name,
        user_seq=user_seq,
        munhak_seq=munhak_seq,
        add_date=datetime.now(),
    )

    db.session.add(tag_row)
    db.session.commit()

    return "", 200


@board_bp.route("/tag/like", methods=["GET", "POST"])
@login_required
def like_tag():
    args = request.form
    tag_seq = args.get("tag_seq", None)
    print(args)
    if tag_seq is None or not tag_seq.isdigit():
        return abort(400)

    tag_seq = int(tag_seq)
    user_seq = session["user"]["user_seq"]
    old_like_row = Like.query.filter_by(tag_seq=tag_seq, user_seq=user_seq).first()

    if old_like_row is None:
        like_row = Like(tag_seq=tag_seq, user_seq=user_seq, add_date=datetime.now())
        db.session.add(like_row)
        db.session.commit()
        return jsonify({"liked": True}), 200
    else:
        db.session.delete(old_like_row)
        db.session.commit()
        return jsonify({"liked": False}), 200


@board_bp.route("/tag/delete", methods=["GET", "POST"])
@login_required
def delete_tag():
    args = request.form
    tag_seq = args.get("tag_seq", None)
    print(args)
    if tag_seq is None or not tag_seq.isdigit():
        return abort(400)

    tag_seq = int(tag_seq)
    user_seq = session["user"]["user_seq"]

    old_tag_row = Tag.query.filter_by(user_seq=user_seq, tag_seq=tag_seq).first()
    if old_tag_row is None:
        return abort(404)

    db.session.delete(old_tag_row)
    db.session.commit()
    return "", 200


@board_bp.route("/video/delete", methods=["GET", "POST"])
@login_required
def delete_video():
    args = request.form
    video_seq = args.get("video_seq", None)
    print(args)
    if video_seq is None or not video_seq.isdigit():
        return abort(400)

    video_seq = int(video_seq)
    user_seq = session["user"]["user_seq"]

    old_video_row = Video.query.filter_by(user_seq=user_seq, video_seq=video_seq).first()
    if old_video_row is None:
        return abort(404)

    db.session.delete(old_video_row)
    db.session.commit()
    return "", 200


@board_bp.route("/video/add", methods=["GET", "POST"])
@login_required
def add_video():
    from urllib import parse

    args = request.form
    munhak_seq = args.get("munhak_seq", None)
    munhak_source = args.get("munhak_source", None)
    video_url = args.get("video_url", None)
    type = args.get("type", None)

    munhak_rows_data = cache.get("munhak_rows_data")
    munhak_rows = copy.deepcopy(munhak_rows_data)

    print(munhak_rows)
    print(munhak_seq)
    print(munhak_source)

    if type == "munhak":
        munhak_seq = int(munhak_seq)
        if len([munhak_row for munhak_row in munhak_rows if munhak_row["munhak_seq"] == munhak_seq]) == 0:
            return abort(404)

    elif type == "exam":
        if len([munhak_row for munhak_row in munhak_rows if munhak_row["source"] == munhak_source]) == 0:
            return abort(404)
    else:
        return abort(404)

    parts = parse.urlparse(video_url)
    query = parse.parse_qs(parts.query)
    print(query)

    video_code = ""
    start_time = "0"

    try:
        if "v" in query:
            video_code = query["v"][0]
            if "t" in query:
                start_time = query["t"][0]
            else:
                start_time = "0"
        else:
            if parts.netloc == "youtu.be":
                video_code = parts.path[1:]
                if "t" in query:
                    start_time = query["t"][0]

                else:
                    start_time = "0"

        if not start_time.isdigit():
            return abort(400)

        video_url = f"https://youtu.be/{video_code}?t={start_time}"
        print(video_url)
        res = requests.get("https://www.googleapis.com/youtube/v3/videos", params={
            "key": YOUTUBE_KEY, "part": "snippet", "id": video_code
        })
        print(res.text)
        video = json.loads(res.text)["items"][0]
    except:
        return abort(400)

    user_seq = session["user"]["user_seq"]

    video_title = video["snippet"]["title"].replace("&#39;", "'")

    video_thumbnail = video["snippet"]["thumbnails"]["standard"]["url"]

    if type == "munhak":
        old_video_row = Video.query.filter_by(munhak_seq=munhak_seq, youtube_code=video_code).first()
        if old_video_row is not None:
            return abort(409)

        video_row = Video(user_seq=user_seq, munhak_seq=munhak_seq, youtube_url=video_url, youtube_title=video_title,
                          youtube_thumbnail=video_thumbnail, add_date=datetime.now(), youtube_code=video_code)
        db.session.add(video_row)
        db.session.commit()
    else:
        old_video_row = Video.query.filter_by(munhak_source=munhak_source, youtube_code=video_code).first()
        if old_video_row is not None:
            return abort(409)

        video_row = Video(user_seq=user_seq, munhak_source=munhak_source, youtube_url=video_url,
                          youtube_title=video_title,
                          youtube_thumbnail=video_thumbnail, add_date=datetime.now(), youtube_code=video_code)
        db.session.add(video_row)
        db.session.commit()

    return "", 200
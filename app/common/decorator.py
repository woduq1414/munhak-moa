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
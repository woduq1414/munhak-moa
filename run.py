#!/usr/bin/env python
from app import create_app
from flask import render_template

# app = create_app('config')
# app.app_context().push()

from app.db import db
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
@app.errorhandler(404)
def not_found(error):
    return render_template('index.html')






if __name__ == '__main__':
    app.run(host=app.config['HOST'],
            port=app.config['PORT'],
            debug=app.config['DEBUG'])

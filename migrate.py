# from flask.ext.script import Manager
# from flask.ext.migrate import Migrate, MigrateCommand
from flask import Flask
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from app.db import  db
app = Flask(__name__, static_url_path='', static_folder='../static', template_folder='../static')

migrate = Migrate(app, db, compare_type=True)

manager = Manager(app)
manager.add_command('db', MigrateCommand)





if __name__ == '__main__':
    manager.run()


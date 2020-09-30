from flask_sqlalchemy import SQLAlchemy, Model
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import relationship, backref
from sqlalchemy import ForeignKey


class CustomModel(Model):
    def as_dict(self):
        temp = {}
        for x in self.__table__.columns:
            if str(type(getattr(self, x.name))) == "<class 'datetime.datetime'>":
                temp[x.name] = str(getattr(self, x.name))
            else:
                temp[x.name] = getattr(self, x.name)
        return temp


db = SQLAlchemy(model_class=CustomModel)


class User(db.Model):
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}

    user_seq = db.Column(db.Integer, primary_key=True, nullable=False)
    nickname = db.Column(db.String, nullable=False)

    social_id = db.Column(db.String(100), nullable=False)
    social_type = db.Column(db.String(20), nullable=False)
    add_date = db.Column(db.DateTime, nullable=False)


class Tag(db.Model):
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}

    tag_seq = db.Column(db.Integer, primary_key=True, nullable=False)

    munhak_seq = db.Column(db.Integer, nullable=False)
    tag_name = db.Column(db.String(20), nullable=False)

    user_seq = db.Column(db.Integer, ForeignKey('user.user_seq' , ondelete='CASCADE'), nullable=False)
    user = relationship("User", backref=backref('tag', order_by=tag_seq, cascade='all,delete'))
    add_date = db.Column(db.DateTime, nullable=False)


class Tip(db.Model):
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}

    tip_seq = db.Column(db.Integer, primary_key=True, nullable=False)

    user_seq = db.Column(db.Integer, ForeignKey('user.user_seq', ondelete='CASCADE'), nullable=False)
    user = relationship("User", backref=backref('tip', order_by=user_seq, cascade='all,delete'))

    munhak_seq = db.Column(db.Integer, nullable=False)
    tip_content = db.Column(db.String(1500), nullable=False)
    add_date = db.Column(db.DateTime, nullable=False)


class Like(db.Model):
    like_seq = db.Column(db.Integer, primary_key=True, nullable=False)

    tip_seq = db.Column(db.Integer, ForeignKey('tip.tip_seq', ondelete='CASCADE'), nullable=True)
    tip = relationship("Tip", backref=backref('like1', order_by=like_seq, cascade='all,delete'))

    tag_seq = db.Column(db.Integer, ForeignKey('tag.tag_seq', ondelete='CASCADE'), nullable=True)
    tag = relationship("Tag", backref=backref('like2', order_by=like_seq, cascade='all,delete'))

    user_seq = db.Column(db.Integer, ForeignKey('user.user_seq', ondelete='CASCADE'), nullable=False)
    user = relationship("User", backref=backref('like3', order_by=user_seq, cascade='all,delete'))

    add_date = db.Column(db.DateTime, nullable=False)


class Video(db.Model):
    video_seq = db.Column(db.Integer, primary_key=True, nullable=False)
    user_seq = db.Column(db.Integer, ForeignKey('user.user_seq', ondelete='CASCADE'), nullable=False)
    user = relationship("User", backref=backref('video', order_by=user_seq, cascade='all,delete'))

    munhak_seq = db.Column(db.Integer, nullable=True)
    munhak_source = db.Column(db.String, nullable=True)

    youtube_url = db.Column(db.String(50), nullable=False)
    youtube_code = db.Column(db.String(20), nullable=False)
    youtube_title = db.Column(db.String(100), nullable=False)
    youtube_thumbnail = db.Column(db.String(100), nullable=False)

    add_date = db.Column(db.DateTime, nullable=False)


class QuizRanking(db.Model):
    record_seq = db.Column(db.Integer, primary_key=True, nullable=False)
    user_seq = db.Column(db.Integer, ForeignKey('user.user_seq', ondelete='CASCADE'), nullable=False)
    user = relationship("User", backref=backref('QuizRanking', order_by=user_seq, cascade='all,delete'))

    score = db.Column(db.Integer, nullable=False)

    record_date = db.Column(db.DateTime, nullable=False)
# -*- coding: utf-8 -*-

from sqlalchemy import Integer, String, Text, Date
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy import asc, or_

from ..helpers import svg_image_url
from ..cacher import cacher

from .. import db


# Icon stuff

class IconLang(db.Model):
    __tablename__ = 'icon_lang'

    id = db.Column('id', String(50), db.ForeignKey('icon.id'), primary_key=True)
    lang = db.Column('lang', String(2), primary_key=True)
    name_lang = db.Column('name', Text)
    description_lang = db.Column('description', Text)
    pending = db.Column('pending', Integer)

    def __repr__(self):
        return '<IconLang %s: %r>' % (self.id, self.name_lang)

class Icon(db.Model):
    __tablename__ = 'icon'

    id = db.Column('id', String(50), primary_key=True)
    name = db.Column('name', Text)
    description = db.Column('description', Text)
    group = db.Column('group', String(50))
    order = db.Column('order', Integer)

    def __repr__(self):
        return '<Icon %s: %r>' % (self.id, self.name)

    @hybrid_property
    def svg_url(self):
        return svg_image_url(self.id + '.svg', 'icons')

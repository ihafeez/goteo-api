# -*- coding: utf-8 -*-

from sqlalchemy import String, Boolean

from .. import db


class Node(db.Model):
    __tablename__ = 'node'

    id = db.Column('id', String(50), primary_key=True)
    name = db.Column('name', String(256))
    active = db.Column('active', Boolean)

    def __repr__(self):
        return '<Node(%d): %s>' % (self.id, self.name)

# -*- coding: utf-8 -*-

#from flask.ext.sqlalchemy import Pagination
from sqlalchemy import func, Integer, String, Text, Date
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy import or_, desc, and_, distinct

from ..helpers import image_url, utc_from_local
from ..decorators import cacher
from .post import Post, Blog
from .. import db

class Project(db.Model):
    __tablename__ = 'project'

    #PROJECT STATUS IDs
    STATUS_REJECTED    = 0
    STATUS_EDITING     = 1 # en negociación
    STATUS_REVIEWING   = 2 #
    STATUS_IN_CAMPAIGN = 3
    STATUS_FUNDED      = 4
    STATUS_FULFILLED   = 5 # 'Caso de exito'
    STATUS_UNFUNDED    = 6 # proyecto fallido

    PUBLISHED_PROJECTS = [STATUS_IN_CAMPAIGN, STATUS_FUNDED, STATUS_FULFILLED, STATUS_UNFUNDED]
    SUCCESSFUL_PROJECTS = [STATUS_IN_CAMPAIGN, STATUS_FUNDED, STATUS_FULFILLED]

    id = db.Column('id', String(50), primary_key=True)
    owner = db.Column('owner', String(50), db.ForeignKey('user.id'))
    name = db.Column('name', Text)
    subtitle = db.Column('subtitle', Text)
    image = db.Column('image', String(255))
    video = db.Column('video', String(255))
    media = db.Column('media', String(255))
    minimum = db.Column('mincost', Integer)
    optimum = db.Column('maxcost', Integer)
    amount = db.Column('amount', Integer)
    status = db.Column('status', Integer)
    date_passed = db.Column('passed', Date)
    created = db.Column('created', Date)
    date_updated = db.Column('updated', Date)
    # deberia haber un campo como el updated solo hasta que se publica el proyecto,
    # luego coincidiria con el publicado
    published = db.Column('published', Date)
    date_closed = db.Column('closed', Date) #
    node = db.Column('node', String(50), db.ForeignKey('node.id'))
    # total_funding
    # active_date
    # rewards
    # platform
    #aportes = db.relationship('Invest', backref='project')

    def __repr__(self):
        return '<Project %s: %s>' % (self.id, self.name)

    @hybrid_property
    def image_url(self):
        return image_url(self.image, size="big")

    @hybrid_property
    def date_created(self):
        return utc_from_local(self.created)

    @hybrid_property
    def date_published(self):
        return utc_from_local(self.published)

    #Filters for this table
    @hybrid_property
    def filters(self):
        return [self.status.in_(self.PUBLISHED_PROJECTS)]

    # Getting filters for this model
    @hybrid_method
    def get_filters(self, **kwargs):
        from .reward import Reward
        from .location import Location, LocationItem
        filters = self.filters
        if 'received' in kwargs and kwargs['received'] is not None:
            filters = [self.date_updated != None, self.date_updated != '0000-00-00']
        if 'successful' in kwargs and kwargs['successful'] is not None:
            filters = [self.date_passed != None, self.date_passed != '0000-00-00']
            filters.append(self.status.in_(self.PUBLISHED_PROJECTS))
            # filters.append(self.status > self.STATUS_REJECTED)
        if 'closed' in kwargs and kwargs['closed'] is not None:
            and1 = and_(self.date_passed != None, self.date_passed != '0000-00-00')
            and2 = and_(self.date_closed != None, self.date_closed != '0000-00-00')
            filters.append(or_(and1, and2))
        if 'finished' in kwargs and kwargs['finished'] is not None:
            filters.append(self.status.in_([self.STATUS_FUNDED, self.STATUS_FULFILLED]))
        if 'failed' in kwargs and kwargs['failed'] is not None:
            filters.append(self.status == self.STATUS_UNFUNDED)

        # # Join project table if filters
        for i in ('license', 'license_type'):
            if i in kwargs and kwargs[i] is not None:
                filters.append(self.id == Reward.project)
        if 'license_type' in kwargs and kwargs['license_type'] is not None:
            filters.append(Reward.type == kwargs['license_type'])
        if 'license' in kwargs and kwargs['license'] is not None:
            filters.append(Reward.license.in_(kwargs['license']))
        if 'status' in kwargs and kwargs['status'] is not None:
            filters.append(self.status.in_(kwargs['status']))
        if 'from_date' in kwargs and kwargs['from_date'] is not None:
            filters.append(self.published >= kwargs['from_date'])
        if 'to_date' in kwargs and kwargs['to_date'] is not None:
            filters.append(self.published <= kwargs['to_date'])
        if 'project' in kwargs and kwargs['project'] is not None:
            filters.append(self.id.in_(kwargs['project']))
        if 'node' in kwargs and kwargs['node'] is not None:
            filters.append(self.node.in_(kwargs['node']))
        if 'category' in kwargs and kwargs['category'] is not None:
            filters.append(self.id == ProjectCategory.project)
            filters.append(ProjectCategory.category.in_(kwargs['category']))
        if 'location' in kwargs and kwargs['location'] is not None:
            subquery = Location.location_subquery(**kwargs['location'])
            filters.append(LocationItem.type == 'project')
            filters.append(LocationItem.item == self.id)
            filters.append(LocationItem.locable == True)
            filters.append(LocationItem.id.in_(subquery))

        return filters

    @hybrid_method
    @cacher
    def total(self, **kwargs):
        """Total number of projects"""
        try:
            filters = list(self.get_filters(**kwargs))
            total = db.session.query(func.count(distinct(self.id))).filter(*filters).scalar()
            if total is None:
                total = 0
            return total
        except MultipleResultsFound:
            return 0

    @hybrid_method
    @cacher
    def pledged_total(self, **kwargs):
        """Total amount of money (€) raised by Goteo"""
        try:
            filters = list(self.get_filters(**kwargs))
            filters.append(self.status.in_(self.SUCCESSFUL_PROJECTS))
            total = db.session.query(func.sum(distinct(self.amount))).filter(*filters).scalar()
            if total is None:
                total = 0
            return total
        except MultipleResultsFound:
            return 0

    @hybrid_method
    @cacher
    def refunded_total(self, **kwargs):
        """Refunded money (€) on failed projects """
        try:
            filters = list(self.get_filters(**kwargs))
            filters.append(self.status == self.STATUS_UNFUNDED)
            total = db.session.query(func.sum(distinct(self.amount))).filter(*filters).scalar()
            if total is None:
                total = 0
            return total
        except MultipleResultsFound:
            return 0

    @hybrid_method
    @cacher
    def percent_pledged_successful(self, **kwargs):
        """Percentage of money raised over the minimum on successful projects"""
        filters = list(self.get_filters(**kwargs))
        filters.append(self.status.in_([self.STATUS_FUNDED,
                                        self.STATUS_FULFILLED]))
        total = db.session.query(func.avg(self.amount / self.minimum * 100 - 100)).filter(*filters).scalar()
        total = 0 if total is None else round(total, 2)
        return total

    @hybrid_method
    @cacher
    def percent_pledged_failed(self, **kwargs):
        """Percentage of money raised over the minimum on failed projects """
        filters = list(self.get_filters(**kwargs))
        filters.append(self.status == self.STATUS_UNFUNDED)
        total = db.session.query(func.avg(self.amount / self.minimum * 100)).filter(*filters).scalar()
        total = 0 if total is None else round(total, 2)
        return total

    @hybrid_method
    @cacher
    def average_minimum(self, **kwargs):
        """Average minimum cost (€) for successful projects (NOTE: this field is not affected by the location filter)"""
        filters = list(self.get_filters(**kwargs))
        filters.append(self.status.in_([self.STATUS_FUNDED, self.STATUS_FULFILLED]))
        total = db.session.query(func.avg(self.minimum)).filter(*filters).scalar()
        total = 0 if total is None else round(total, 2)
        return total

    @hybrid_method
    @cacher
    def average_total(self, **kwargs):
        """Average money raised (€) for projects"""
        filters = list(self.get_filters(**kwargs))
        total = db.session.query(func.avg(self.amount)).filter(*filters).scalar()
        total = 0 if total is None else round(total, 2)
        return total

    @hybrid_method
    @cacher
    def average_posts(self, **kwargs):
        """Average number of posts by projects"""
        filters = list(self.get_filters(**kwargs))
        filters.append(Post.publish == 1)
        sq1 = db.session.query(func.count(self.id).label('posts')).select_from(Post)\
                            .join(Blog, and_(Blog.id == Post.blog, Blog.type == 'project'))\
                            .join(self, self.id == Blog.owner)\
                            .filter(*filters).group_by(Post.blog).subquery()
        total = db.session.query(func.avg(sq1.c.posts)).scalar()
        total = 0 if total is None else round(total, 2)
        return total

    @hybrid_method
    @cacher
    def collaborated_list(self, **kwargs):
        """Get a list of projects with more collaborations"""
        from .message import Message
        limit = kwargs['limit'] if 'limit' in kwargs else 10
        page = kwargs['page'] if 'page' in kwargs else 0
        filters = list(self.get_filters(**kwargs))

        res = db.session.query(self.id.label('project'),
                               self.name,
                               self.subtitle,
                               self.image,
                               self.media,
                               self.published,
                               func.count(Message.id).label('total')).join(Message)\
                            .filter(*filters).group_by(Message.project)\
                            .order_by(desc('total')).offset(page * limit).limit(limit)

        ret = []
        for u in res:
            u = u._asdict()
            ret.append(u)
        return ret

    @hybrid_method
    @cacher
    def donated_list(self, **kwargs):
        """Get a list of projects with more donations (by individual contributions)"""
        from .invest import Invest
        limit = kwargs['limit'] if 'limit' in kwargs else 10
        page = kwargs['page'] if 'page' in kwargs else 0
        filters = list(self.get_filters(**kwargs))

        res = db.session.query(self.id.label('project'),
                       self.name,
                       self.subtitle,
                       self.image,
                       self.media,
                       self.published,
                       func.count(Invest.id).label('total')).join(Invest)\
                            .filter(*filters).group_by(Invest.project)\
                            .order_by(desc('total')).offset(page * limit).limit(limit)

        ret = []
        for u in res:
            u = u._asdict()
            ret.append(u)
        return ret

    @hybrid_method
    @cacher
    def received_list(self, **kwargs):
        """Get a list of projects with more donations (by amount)"""

        from .invest import Invest

        limit = kwargs['limit'] if 'limit' in kwargs else 10
        page = kwargs['page'] if 'page' in kwargs else 0
        filters = list(self.get_filters(**kwargs))

        filters.append(Invest.status.in_([Invest.STATUS_PENDING,
                                                  Invest.STATUS_CHARGED,
                                                  Invest.STATUS_PAID]))
        res = db.session.query(Project.id.label('project'),
                               Project.name,
                               Project.subtitle,
                               Project.image,
                               Project.media,
                               Project.published,
                               func.sum(Invest.amount).label('amount')).join(Invest)\
                                    .filter(*filters).group_by(Invest.project)\
                                    .order_by(desc('amount')).offset(page * limit).limit(limit)
        ret = []
        for u in res:
            u = u._asdict()
            ret.append(u)
        return ret

class ProjectCategory(db.Model):
    __tablename__ = 'project_category'

    project = db.Column('project', String(50), db.ForeignKey('project.id'), primary_key=True)
    category = db.Column('category', Integer, db.ForeignKey('category.id'), primary_key=True)

    def __repr__(self):
        return '<Category %s>' % (self.project)


# -*- coding: utf-8 -*-

import time

from flask.ext.restful import fields, marshal
from flask.ext.sqlalchemy import sqlalchemy
from flask_restful_swagger import swagger
from sqlalchemy import and_, desc
from sqlalchemy.orm import aliased

from api import db

from api.models.call import Call
from api.models.category import Category, CategoryLang
from api.models.project import Project, ProjectCategory
from api.models.invest import Invest, InvestNode
from api.models.message import Message
from api.models.user import User, UserInterest, UserRole
from api.models.location import Location, LocationItem
from api.decorators import *
from api.helpers import get_lang, image_url, user_url
from api.base_endpoint import BaseList as Base, Response

func = sqlalchemy.func

@swagger.model
class CategoryUsers:
    resource_fields = {
        'id'              : fields.Integer,
        'name'            : fields.String,
        'percentage-users': fields.Float,
        'users'           : fields.Integer
    }
    required = resource_fields.keys()

@swagger.model
class UserDonation:
    resource_fields = {
        'user'         : fields.String,
        'name'              : fields.String,
        'profile-image-url' : fields.String,
        'profile-url' : fields.String,
        'amount'       : fields.Float,
        'contributions': fields.Integer
    }
    required = resource_fields.keys()

@swagger.model
class UserCollaboration:
    resource_fields = {
        'user'              : fields.String,
        'name'              : fields.String,
        'profile-image-url' : fields.String,
        'profile-url' : fields.String,
        'interactions'      : fields.Integer
    }
    required = resource_fields.keys()

@swagger.model
@swagger.nested(**{
                'categories'         :CategoryUsers.__name__,
                'top10-donors'       :UserDonation.__name__,
                'top10-multidonors'  :UserDonation.__name__,
                'top10-collaborators':UserCollaboration.__name__
                }
            )
class CommunityResponse(Response):
    """CommunityResponse"""

    resource_fields = {
        "users"                            : fields.Integer,
        "donors"                           : fields.Integer,
        "percentage-donors-users"          : fields.Float,
        "percentage-unsubscribed-users"    : fields.Float,
        "donors-collaborators"             : fields.Integer,
        "multidonors"                      : fields.Integer,
        "percentage-multidonor-donors"     : fields.Float,
        "percentage-multidonor-users"      : fields.Float,
        "paypal-donors"                    : fields.Integer,
        "creditcard-donors"                : fields.Integer,
        "cash-donors"                      : fields.Integer,
        "collaborators"                    : fields.Integer,
        'average-donors'                   : fields.Integer,
        'average-collaborators'            : fields.Integer,
        'creators-donors'                  : fields.Integer,
        'creators-collaborators'           : fields.Integer,
        'leading-category'                 : fields.Integer,
        'second-category'                  : fields.Integer,
        'users-leading-category'           : fields.Integer,
        'users-second-category'            : fields.Integer,
        'percentage-users-leading-category': fields.Float,
        'percentage-users-second-category' : fields.Float,
        'categories'                       : fields.List(fields.Nested(CategoryUsers.__name__)),
        "top10-donors"                     : fields.List(fields.Nested(UserDonation.__name__)),
        "top10-multidonors"                : fields.List(fields.Nested(UserDonation.__name__)),
        "top10-collaborators"              : fields.List(fields.Nested(UserCollaboration.__name__))
    }

    required = resource_fields.keys()


class CommunityAPI(Base):
    """Get Community Statistics"""

    def __init__(self):
        super(CommunityAPI, self).__init__()

    @swagger.operation(
        notes='Community report',
        responseClass=CommunityResponse.__name__,
        nickname='community',
        parameters=Base.INPUT_FILTERS,
        responseMessages=Base.RESPONSE_MESSAGES
    )
    @requires_auth
    @ratelimit()
    def get(self):
        """Get the community reports
        <a href="http://developers.goteo.org/doc/reports#community">developers.goteo.org/doc/reports#community</a>
        """
        ret = self._get()
        return ret.response()

    def _get(self):
        """Get()'s method dirty work"""
        time_start = time.time()
        # remove not used args
        args = self.parse_args(remove=('page','limit'))


        filters = []
        filters_categories = [Category.name != '']  # para categorias
        filters_collaborators = []  # para las relacionadas con Colaboradores
        if args['from_date']:
            filters.append(Invest.date_invested >= args['from_date'])
            filters_categories.append(Invest.date_invested >= args['from_date'])
            filters_categories.append(Invest.user == UserInterest.user)
            filters_collaborators.append(Message.date >= args['from_date'])
        if args['to_date']:
            filters.append(Invest.date_invested <= args['to_date'])
            filters_categories.append(Invest.date_invested <= args['to_date'])
            filters_categories.append(Invest.user == UserInterest.user)
            filters_collaborators.append(Message.date <= args['to_date'])
        if args['project']:
            filters.append(Invest.project.in_(args['project']))
            filters_categories.append(Invest.project.in_(args['project']))
            filters_categories.append(UserInterest.user == Invest.user)
            filters_collaborators.append(Message.project.in_(args['project']))
        if args['node']:
            #TODO: project_node o invest_node?
            filters.append(Invest.id == InvestNode.invest_id)
            filters.append(InvestNode.invest_node.in_(args['node']))
            filters_categories.append(UserInterest.user == User.id)
            filters_categories.append(User.node.in_(args['node']))
            filters_collaborators.append(Message.user == User.id)
            filters_collaborators.append(User.node.in_(args['node']))
        if args['category']:

            filters.append(Invest.project == ProjectCategory.project)
            filters.append(ProjectCategory.category.in_(args['category']))
            filters_collaborators.append(Message.project == ProjectCategory.project)
            filters_collaborators.append(ProjectCategory.category.in_(args['category']))
        if args['location']:
            # Filtra por la localización del usuario
            locations_ids = Location.location_ids(**args['location'])

            if locations_ids == []:
                return bad_request("No locations in the specified range")

            filters.append(Invest.user == LocationItem.item)
            filters.append(LocationItem.type == 'user')
            filters.append(LocationItem.id.in_(locations_ids))
            filters_categories.append(UserInterest.user == LocationItem.item)
            filters_categories.append(LocationItem.type == 'user')
            filters_categories.append(LocationItem.id.in_(locations_ids))
            filters_collaborators.append(Message.user == LocationItem.item)
            filters_collaborators.append(LocationItem.type == 'user')
            filters_collaborators.append(LocationItem.id.in_(locations_ids))

        users = User.total(**args)
        nargs = args.copy();
        nargs['unsubscribed'] = 1;
        bajas = User.total(**nargs)
        donors = Invest.donors_total(**args)
        multidonors = Invest.multidonors_total(**args)

        paypal_donors = Invest.donors_total(**dict(args, **{'method' : Invest.METHOD_PAYPAL}))
        creditcard_donors = Invest.donors_total(**dict(args, **{'method' : Invest.METHOD_TPV}))
        cash_donors = Invest.donors_total(**dict(args, **{'method' : Invest.METHOD_CASH}))
        # paypal_multidonors = Invest.multidonors_total(**nargs)
        categorias = self._categorias(list(filters_categories), args['lang'])
        users_categoria1 = categorias[0].users if len(categorias) > 0 else None
        users_categoria2 = categorias[1].users if len(categorias) > 1 else None

        # Listado de usuarios que no cuentan para estadisticias (admin, convocatorias)
        admines = db.session.query(UserRole.user_id).filter(UserRole.role_id == 'superadmin').all()
        convocadores = db.session.query(Call.owner).filter(Call.status > Call.STATUS_REVIEWING).all()
        users_exclude = map(lambda c: c[0], admines)
        users_exclude.extend(map(lambda c: c[0], convocadores))
        # convertir en conjunto para evitar repeticiones
        users_exclude = set(users_exclude)

        top10_multidonors = []
        for u in self._top10_multidonors(list(filters), users_exclude):
            u = u._asdict()
            item = marshal(u, UserDonation.resource_fields)
            item['profile-image-url'] = image_url(u['avatar'])
            item['profile-url'] = user_url(u['id'])
            top10_multidonors.append(item)

        top10_donors = []
        for u in self._top10_donors(list(filters), users_exclude):
            u = u._asdict()
            item = marshal(u, UserDonation.resource_fields)
            item['profile-image-url'] = image_url(u['avatar'])
            item['profile-url'] = user_url(u['id'])
            top10_donors.append(item)

        top10_collaborations = []
        for u in self._top10_collaborations(list(filters_collaborators)):
            u = u._asdict()
            item = marshal(u, UserDonation.resource_fields)
            item['profile-image-url'] = image_url(u['avatar'])
            item['profile-url'] = user_url(u['id'])
            top10_collaborations.append(item)

        res = CommunityResponse(
            starttime = time_start,
            attributes = {
                'users'                             : users,
                'donors'                            : donors,
                'multidonors'                       : multidonors,
                'percentage-donors-users'           : percent(donors, users),
                'percentage-unsubscribed-users'     : percent(bajas, users),
                'percentage-multidonor-donors'      : percent(multidonors, donors),
                'percentage-multidonor-users'       : percent(multidonors, users),
                'collaborators'                     : Message.collaborators_total(**args),
                'paypal-donors'                     : paypal_donors,
                'creditcard-donors'                 : creditcard_donors,
                'cash-donors'                       : cash_donors,
                'donors-collaborators'              : self._coficolaboradores(list(filters)),
                'average-donors'                    : self._media_cofi(list(filters)),
                'average-collaborators'             : self._media_colab(list(filters_collaborators)),
                'creators-donors'                   : self._impulcofinanciadores(list(filters)),
                'creators-collaborators'            : self._impulcolaboradores(list(filters_collaborators)),
                'categories'                        : map(lambda t: {t.id: {'users': t.users, 'id': t.id, 'name': t.name, 'percentage-users': percent(t.users, users)}}, categorias),
                'leading-category'                  : categorias[0].id if len(categorias) > 0 else None,
                'users-leading-category'            : users_categoria1,
                'percentage-users-leading-category' : percent(users_categoria1, users),
                'second-category'                   : categorias[1].id if len(categorias) > 1 else None,
                'users-second-category'             : users_categoria2,
                'percentage-users-second-category'  : percent(users_categoria2, users),
                'top10-multidonors'                 : top10_multidonors,
                'top10-donors'                      : top10_donors,
                'top10-collaborators'               : top10_collaborations,
            },
            filters = args.items()
        )
        return res


    # Número de colaboradores
    def _colaboradores(self, f_colaboradores = []):
        res = db.session.query(func.count(func.distinct(Message.user))).filter(*f_colaboradores).scalar()
        if res is None:
            res = 0
        return res

    # Cofinanciadores que colaboran
    def _coficolaboradores(self, f_coficolaboradores = []):
        sq_blocked = db.session.query(Message.id).filter(Message.blocked == 1).subquery()
        f_coficolaboradores.append(Message.thread > 0)
        f_coficolaboradores.append(Message.thread.in_(sq_blocked))
        f_coficolaboradores.append(Invest.status.in_([Invest.STATUS_PENDING,
                                                      Invest.STATUS_CHARGED,
                                                      Invest.STATUS_PAID,
                                                      Invest.STATUS_RETURNED]))
        res = db.session.query(func.count(func.distinct(Invest.user)))\
                                            .join(Message, Message.user == Invest.user)\
                                            .filter(*f_coficolaboradores).scalar()
        if res is None:
            res = 0
        return res

    # Media de cofinanciadores por proyecto exitoso
    def _media_cofi(self, f_media_cofi = []):
        f_media_cofi.append(Project.status.in_([Project.STATUS_FUNDED,
                                                Project.STATUS_FULFILLED]))
        sq = db.session.query(func.count(func.distinct(Invest.user)).label("co"))\
                                    .join(Project, Invest.project == Project.id)\
                                    .filter(*f_media_cofi).group_by(Invest.project).subquery()
        res = db.session.query(func.avg(sq.c.co)).scalar()
        if res is None:
            res = 0
        return res

    # Media de colaboradores por proyecto
    def _media_colab(self, f_media_colab = []):
        f_media_colab.append(Project.status.in_([Project.STATUS_FUNDED,
                                                 Project.STATUS_FULFILLED]))
        sq = db.session.query(func.count(func.distinct(Message.user)).label("co"))\
                                    .join(Project, Message.project == Project.id)\
                                    .filter(*f_media_colab).group_by(Message.project).subquery()
        res = db.session.query(func.avg(sq.c.co)).scalar()
        if res is None:
            res = 0
        return res

    # Núm. impulsores que cofinancian a otros
    def _impulcofinanciadores(self, f_impulcofinanciadores = []):
        f_impulcofinanciadores.append(Invest.status.in_([Invest.STATUS_PAID,
                                                         Invest.STATUS_RETURNED,
                                                         Invest.STATUS_RELOCATED]))
        f_impulcofinanciadores.append(Invest.project != Project.id)
        res = db.session.query(func.count(func.distinct(Invest.user)))\
                                    .join(Project, and_(Project.owner == Invest.user, Project.status.in_([
                                        Project.STATUS_FUNDED,
                                        Project.STATUS_FULFILLED,
                                        Project.STATUS_IN_CAMPAIGN,
                                        Project.STATUS_UNFUNDED
                                     ])))\
                                    .filter(*f_impulcofinanciadores).scalar()
        if res is None:
            res = 0
        return res

    # Núm. impulsores que colaboran con otros
    def _impulcolaboradores(self, f_impulcolaboradores = []):
        sq_blocked = db.session.query(Message.id).filter(Message.blocked == 1).subquery()
        f_impulcolaboradores.append(Message.thread > 0)
        f_impulcolaboradores.append(Message.thread.in_(sq_blocked))
        f_impulcolaboradores.append(Message.project != Project.id)
        res = db.session.query(func.count(func.distinct(Message.user)))\
                                    .join(Project, and_(Project.owner == Message.user, Project.status.in_([
                                        Project.STATUS_FUNDED,
                                        Project.STATUS_FULFILLED,
                                        Project.STATUS_IN_CAMPAIGN,
                                        Project.STATUS_UNFUNDED
                                    ])))\
                                    .filter(*f_impulcolaboradores).scalar()
        if res is None:
            res = 0
        return res

    # Lista de categorias
    # TODO: idiomas para los nombres de categorias aqui
    def _categorias(self, f_categorias = [], langs = []):
        # In case of requiring languages, a LEFT JOIN must be generated
        cols = [func.count(UserInterest.user).label('users'), Category.id, Category.name]
        if langs:
            joins = []
            _langs = {}
            for l in langs:
                _langs[l] = aliased(CategoryLang)
                cols.append(_langs[l].name_lang.label('name_' + l))
                joins.append((_langs[l], and_(_langs[l].id == Category.id, _langs[l].lang == l)))
            query = db.session.query(*cols).join(Category, Category.id == UserInterest.interest).outerjoin(*joins)
        else:
            query = db.session.query(*cols).join(Category, Category.id == UserInterest.interest)
        ret = []

        for u in query.filter(*f_categorias).group_by(UserInterest.interest)\
                      .order_by(desc(func.count(UserInterest.user))):
            # u = u._asdict()
            u.name = get_lang(u._asdict(), 'name', langs)
            ret.append(u)
        if ret is None:
            ret = []
        return ret


    # Top 10 Cofinanciadores (con mayor numero de contribuciones, excepto usuarios convocadores o superadmins)
    def _top10_multidonors(self, f_top10_multidonors = [], users_exclude = []):
        f_top10_multidonors.append(Invest.status.in_([Invest.STATUS_PENDING,
                                                 Invest.STATUS_CHARGED,
                                                 Invest.STATUS_PAID,
                                                 Invest.STATUS_RETURNED]))
        f_top10_multidonors.append(Invest.user == User.id)
        f_top10_multidonors.append(~Invest.user.in_(users_exclude))
        res = db.session.query(Invest.user, User.name, User.id, User.avatar, func.count(Invest.id).label('contributions'), func.sum(Invest.amount).label('amount'))\
                                    .filter(*f_top10_multidonors).group_by(Invest.user)\
                                    .order_by(desc('contributions'), desc('amount')).limit(10).all()
        if res is None:
            res = []
        return res


    # Top 10 Cofinanciadores con más caudal (más generosos) excluir usuarios convocadores Y ADMINES
    def _top10_donors(self, f_top10_donors = [], users_exclude = []):
        f_top10_donors.append(Invest.status.in_([Invest.STATUS_PENDING,
                                                      Invest.STATUS_CHARGED,
                                                      Invest.STATUS_PAID,
                                                      Invest.STATUS_RETURNED]))
        f_top10_donors.append(Invest.user == User.id)
        f_top10_donors.append(~Invest.user.in_(users_exclude))
        res = db.session.query(Invest.user, User.name, User.id, User.avatar, func.count(Invest.id).label('contributions'), func.sum(Invest.amount).label('amount'))\
                                    .filter(*f_top10_donors).group_by(Invest.user)\
                                    .order_by(desc('amount'), desc('contributions')).limit(10).all()
        if res is None:
            res = []
        return res

    # Top 10 colaboradores
    def _top10_collaborations(self, f_top10_collaborations = []):
        f_top10_collaborations.append(Message.user == User.id)
        res = db.session.query(Message.user, User.name, User.id, User.avatar, func.count(Message.id).label('interactions'))\
                            .filter(*f_top10_collaborations).group_by(Message.user)\
                            .order_by(desc('interactions')).limit(10).all()
        if res is None:
            res = []
        return res


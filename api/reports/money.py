# -*- coding: utf-8 -*-
from model import app, db
from model import Project, ProjectCategory, Category, Invest, Call, Cost, InvestNode, Location, LocationItem

from flask import abort, jsonify
from flask.ext.restful import Resource, reqparse, fields, marshal
from flask.ext.sqlalchemy import sqlalchemy
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from datetime import date

from decorators import *
from config import config

import time

# DEBUG
if config.debug:
    db.session.query = debug_time(db.session.query)

invest_fields = {
    'id': fields.Integer,
    'user': fields.String,
    'project': fields.String,
    'status': fields.Integer,
    'amount': fields.Integer
}

func = sqlalchemy.func


@swagger.model
class MoneyResponse:
    """MoneyResponse"""
    __name__ = "MoneyResponse"

    resource_fields = {
        "average-failed": fields.Float,
        "average-invest": fields.Float,
        "average-invest-paypal": fields.Float,
        "average-mincost": fields.Float,
        "average-received": fields.Float,
        "average-second-round": fields.Float,
        "call-amount": fields.Integer,
        "call-committed-amount": fields.Integer,
        "cash-amount": fields.Integer,
        "committed": fields.Integer,
        "comprometido-fail": fields.Float,
        "comprometido-success": fields.Float,
        "devuelto": fields.Integer,
        "fee-amount": fields.Float,
        "paypal-amount": fields.Integer,
        "tpv-amount": fields.Integer
    }

    required = resource_fields.keys()


class MoneyAPI(Resource):
    """Get Money Statistics"""

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('from_date', type=str)
        self.reqparse.add_argument('to_date', type=str)
        self.reqparse.add_argument('node', type=str, action='append')
        self.reqparse.add_argument('project', type=str, action='append')
        self.reqparse.add_argument('category', type=str)
        self.reqparse.add_argument('location', type=str)
        super(MoneyAPI, self).__init__()

    invalid_input = {
        "code": 400,
        "message": "Invalid parameters"
    }

    @swagger.operation(
    summary='Money report',
    notes='Money report',
    responseClass='MoneyResponse',
    nickname='money',
    parameters=[
        {
            "paramType": "query",
            "name": "project",
            "description": "Filter by individual project(s) separated by commas",
            "required": False,
            "dataType": "string",
            "allowMultiple": True
        },
        {
            "paramType": "query",
            "name": "from_date",
            "description": 'Filter from date. Ex. "2013-01-01"',
            "required": False,
            "dataType": "string"
        },
        {
            "paramType": "query",
            "name": "to_date",
            "description": 'Filter until date.. Ex. "2014-01-01"',
            "required": False,
            "dataType": "string"
        },
        {
            "paramType": "query",
            "name": "node",
            "description": 'Filter by individual node(s) separated by commas',
            "required": False,
            "dataType": "string"
        },
        {
            "paramType": "query",
            "name": "category",
            "description": 'Filter by project category',
            "required": False,
            "dataType": "string"
        },
        {
            "paramType": "query",
            "name": "location",
            "description": 'Filter by project location (Lat,lon,Km)',
            "required": False,
            "dataType": "string"
        }

    ],
    responseMessages=[invalid_input])
    @requires_auth
    @ratelimit()
    def get(self):
        """Get the Money Report
        <a href="http://developers.goteo.org/reports#money">developers.goteo.org/reports#money</a>
        """
        time_start = time.time()

        args = self.reqparse.parse_args()

        filters = []
        filters2 = []  # para average_mincost
        filters3 = []  # para call_committed_amount
        if args['from_date']:
            filters.append(Invest.date_invested >= args['from_date'])
            filters2.append(Invest.date_invested >= args['from_date'])
            filters3.append(Call.date_published >= args['from_date'])
        if args['to_date']:
            filters.append(Invest.date_invested <= args['to_date'])
            filters2.append(Invest.date_invested <= args['to_date'])
            filters3.append(Call.date_published <= args['to_date'])
        if args['project']:
            filters.append(Invest.project.in_(args['project']))
            filters2.append(Project.id.in_(args['project']))
            # no afecta a filters3
        if args['node']:
            filters.append(Invest.id == InvestNode.invest_id)
            filters2.append(Project.id == InvestNode.project_id)
            filters.append(InvestNode.invest_node.in_(args['node']))
            filters2.append(InvestNode.invest_node.in_(args['node']))
            # FIXME: Call.node?
        if args['category']:
            try:
                category_id = db.session.query(Category.id).filter(Category.name == args['category']).one()
                category_id = category_id[0]
            except NoResultFound:
                return {"error": "Invalid category"}, 400

            filters.append(Invest.project == ProjectCategory.project)
            filters2.append(Invest.project == ProjectCategory.project)
            filters.append(ProjectCategory.category == category_id)
            filters2.append(ProjectCategory.category == category_id)
            # no afecta a filters3
        if args['location']:
            location = args['location'].split(",")
            if len(location) != 3:
                return {"error": "Invalid parameter: location"}, 400

            from geopy.distance import VincentyDistance
            latitude, longitude, radius = location

            radius = int(radius)
            if radius > 500 or radius < 0:
                return {"error": "Radius must be a value between 0 and 500 Km"}, 400

            locations = db.session.query(Location.id, Location.lat, Location.lon).all()
            locations = filter(lambda l: VincentyDistance((latitude, longitude), (l[1], l[2])).km <= radius, locations)
            locations_ids = map(lambda l: int(l[0]), locations)

            if locations_ids == []:
                return {"error": "No locations in the specified range"}, 400

            filters.append(Invest.user == LocationItem.item)
            filters.append(LocationItem.type == 'user')
            filters.append(LocationItem.id.in_(locations_ids))
            # no afecta a filters2 ni filters3


        # TODO: Qué mostrar cuando no hay resultados?
        # return jsonify({})

        # -  [Renombrar dinero comprometido] Suma recaudada por la plataforma
        comprometido = self._comprometido(list(filters))

        # - Dinero devuelto (en proyectos archivados)
        devuelto = self._devuelto(list(filters))

        #- Recaudado mediante PayPal
        #FIXME: No quitamos los devueltos?
        paypal_amount = self._paypal_amount(list(filters))

        #- Recaudado mediante TPV
        #FIXME: No quitamos los devueltos?
        tpv_amount = self._tpv_amount(list(filters))

        # - [Renombrar aportes manuales] Recaudado mediante transferencia bancaria directa
        #FIXME: No quitamos los devueltos?
        cash_amount = self._cash_amount(list(filters))

        # - [Renombrar] Capital Riego de Goteo (fondos captados de instituciones y empresas destinados a la bolsa de Capital Riego https://goteo.org/service/resources)
        call_committed_amount = self._call_committed_amount(list(filters3))

        # - [NEW] Suma recaudada en Convocatorias (Capital riego distribuido + crowd)
        #FIXME: No quitamos los devueltos?
        call_amount = self._call_amount(list(filters))

        # - Total 8% recaudado por Goteo
        fee_amount = self._fee_amount(list(filters))

        # - Aporte medio por cofinanciador(micromecenas)
        # OJO: En reporting.php no calcula esto mismo
        average_donation = self._average_donation(list(filters))

        # - Aporte medio por cofinanciador(micromecenas) mediante PayPal
        # OJO: En reporting.php no calcula esto mismo
        average_donation_paypal = self._average_donation_paypal(list(filters))

        # - (Renombrar Coste mínimo medio por proyecto exitoso ] Presupuesto mínimo medio por proyecto exitoso
        # TODO: ¿parametro location?
        # OJO: En reporting.php no calcula esto mismo
        average_mincost = self._average_mincost(list(filters2))

        # - Recaudación media por proyecto exitoso ( financiado )
        average_received = self._average_received(list(filters))

        # - Perc. medio de recaudación sobre el mínimo (número del dato anterior)
        comprometido_success = self._comprometido_success(list(filters))

        # (Nuevo) Dinero medio solo obtenido en 2a ronda
        average_second_round = self._average_second_round(list(filters))

        # - [Renombrar Dinero compr. medio en proyectos archivados] Dinero recaudado de media en campañas fallidas
        average_failed = self._average_failed(list(filters))

        # - [Renombrar]Perc. dinero compr. medio (dinero recaudado de media) sobre mínimo (número del dato anterior)
        # Perc. dinero compr. medio sobre mínimo',
        comprometido_fail = self._comprometido_fail(list(filters))

        # No se pueden donar centimos no? Hacer enteros?
        res = {
                'average-failed': average_failed,
                'average-donation': average_donation,
                'average-donation-paypal': average_donation_paypal,
                'average-minimum': average_mincost,
                'average-received': average_received,
                'average-second-round': average_second_round,
                'matchfund-amount': call_amount,
                'matchfundpledge-amount': call_committed_amount,
                'cash-amount': cash_amount,
                'pledged': comprometido,
                'pledged-failed': comprometido_fail,
                'pledged-successful': comprometido_success,
                'refunded': devuelto,
                'fee-amount': fee_amount,
                'paypal-amount': paypal_amount,
                'creditcard-amount': tpv_amount,
                #'projects': map(lambda i: [i[0], {'recaudado': i[1]}], comprometido),
              }

        res['time-elapsed'] = time.time() - time_start
        res['filters'] = {}
        for k, v in args.items():
            if v is not None:
                res['filters'][k] = v

        return jsonify(res)
        #return {'invests': map(lambda i: {i.investid: marshal(i, invest_fields)}, invests)}

    def _comprometido(self, f_comprometido=[]):
        f_comprometido.append(Invest.status.in_([0, 1, 3, 4]))
        comprometido = db.session.query(func.sum(Invest.amount)).filter(*f_comprometido).scalar()
        if comprometido is None:
            comprometido = 0
        return comprometido

    def _devuelto(self, f_devuelto=[]):
        f_devuelto.append(Invest.status==4)
        devuelto = db.session.query(func.sum(Invest.amount)).filter(*f_devuelto).scalar()
        if devuelto is None:
            devuelto = 0
        return devuelto

    def _paypal_amount(self, f_paypal_amount=[]):
        f_paypal_amount.append(Invest.method==Invest.METHOD_PAYPAL)
        paypal_amount = db.session.query(func.sum(Invest.amount)).filter(*f_paypal_amount).scalar()
        if paypal_amount is None:
            paypal_amount = 0
        return paypal_amount

    def _tpv_amount(self, f_tpv_amount=[]):
        f_tpv_amount.append(Invest.method==Invest.METHOD_TPV)
        tpv_amount = db.session.query(func.sum(Invest.amount)).filter(*f_tpv_amount).scalar()
        if tpv_amount is None:
            tpv_amount = 0
        return tpv_amount

    def _cash_amount(self, f_cash_amount=[]):
        f_cash_amount.append(Invest.method==Invest.METHOD_CASH)
        cash_amount = db.session.query(func.sum(Invest.amount)).filter(*f_cash_amount).scalar()
        if cash_amount is None:
            cash_amount = 0
        return cash_amount

    def _call_committed_amount(self, f_call_committed_amount=[]):
        f_call_committed_amount.append(Call.status > 2)
        call_committed_amount = db.session.query(func.sum(Call.amount)).filter(*f_call_committed_amount).scalar()
        if call_committed_amount is None:
            call_committed_amount = 0
        return call_committed_amount

    def _call_amount(self, f_call_amount=[]):
        f_call_amount.append(Invest.method==Invest.METHOD_DROP)
        f_call_amount.append(Invest.call != None)
        f_call_amount.append(Invest.status.in_([1, 3]))
        call_amount = db.session.query(func.sum(Invest.amount)).filter(*f_call_amount).scalar()
        if call_amount is None:
            call_amount = 0
        return call_amount

    def _fee_amount(self, f_fee_amount=[]):
        f_fee_amount.append(Project.status.in_([4, 5]))
        f_fee_amount.append(Invest.status.in_([1, 3]))
        fee_amount = db.session.query(func.sum(Invest.amount)).join(Project).filter(*f_fee_amount).scalar()
        if fee_amount is None:
            fee_amount = 0
        else:
            fee_amount = float(fee_amount) * 0.08
            fee_amount = round(fee_amount, 2)
        return fee_amount

    def _average_donation(self, f_average_invest=[]):
        f_average_invest.append(Project.status.in_([4, 5, 6]))
        f_average_invest.append(Invest.status > 0)
        sub1 = db.session.query(func.avg(Invest.amount).label('amount')).join(Project)\
                                .filter(*f_average_invest).group_by(Invest.user).subquery()
        average_invest = db.session.query(func.avg(sub1.c.amount)).scalar()
        average_invest = 0 if average_invest is None else round(average_invest, 2)
        return average_invest

    def _average_donation_paypal(self, f_average_donation_paypal=[]):
        f_average_donation_paypal.append(Project.status.in_([4, 5, 6]))
        f_average_donation_paypal.append(Invest.status > 0)
        f_average_donation_paypal.append(Invest.method==Invest.METHOD_PAYPAL)
        sub1 = db.session.query(func.avg(Invest.amount).label('amount')).join(Project)\
                                        .filter(*f_average_donation_paypal).group_by(Invest.user).subquery()
        average_donation_paypal = db.session.query(func.avg(sub1.c.amount)).scalar()
        average_donation_paypal = 0 if average_donation_paypal is None else round(average_donation_paypal, 2)
        return average_donation_paypal

    def _average_mincost(self, f_average_mincost=[]):
        f_average_mincost.append(Project.status.in_([4, 5]))
        average_mincost = db.session.query(func.avg(Project.minimum)).filter(*f_average_mincost).scalar()
        average_mincost = 0 if average_mincost is None else round(average_mincost, 2)
        return average_mincost

    def _average_received(self, f_average_received=[]):
        f_average_received.append(Invest.status.in_([1, 3]))
        f_average_received.append(Project.status.in_([4, 5]))
        average_received = db.session.query(func.sum(Invest.amount) / func.count(func.distinct(Project.id)))\
                                    .join(Project).filter(*f_average_received).scalar()
        average_received = 0 if average_received is None else round(average_received, 2)
        return average_received

    def _comprometido_success(self, f_comprometido_success=[]):
        # FIXME: - 100
        f_comprometido_success.append(Invest.status.in_([1, 3]))
        f_comprometido_success.append(Project.status.in_([4, 5]))
        sub = db.session.query((func.sum(Invest.amount) / Project.minimum * 100 - 100).label('percent'))\
                            .select_from(Invest).join(Project)\
                            .filter(*f_comprometido_success).group_by(Invest.project).subquery()
        comprometido_success = db.session.query(func.avg(sub.c.percent)).scalar()
        comprometido_success = 0 if comprometido_success is None else round(comprometido_success, 2)
        return comprometido_success

    def _average_second_round(self, f_average_second_round=[]):
        f_average_second_round.append(Invest.date_invested >= Project.date_passed)
        sub = db.session.query(func.sum(Invest.amount).label('amount')).join(Project)\
                                            .filter(*f_average_second_round).group_by(Project.id).subquery()
        average_second_round = db.session.query(func.avg(sub.c.amount)).scalar()
        average_second_round = 0 if average_second_round is None else round(average_second_round, 2)
        return average_second_round

    def _average_failed(self, f_average_failed=[]):
        f_average_failed.append(Project.status == 6)
        f_average_failed.append(Invest.status.in_([0, 4]))
        average_failed = db.session.query(func.sum(Invest.amount) / func.count(func.distinct(Project.id)))\
                                        .join(Project).filter(*f_average_failed).scalar()
        average_failed = 0 if average_failed is None else round(average_failed, 2)
        return average_failed

    def _comprometido_fail(self, f_comprometido_fail=[]):
        f_comprometido_fail.append(Invest.status.in_([0, 4]))
        f_comprometido_fail.append(Project.status == 6)
        sub = db.session.query((func.sum(Invest.amount) / Project.minimum * 100).label('percent'))\
                            .select_from(Invest).join(Project)\
                            .filter(*f_comprometido_fail).group_by(Invest.project).subquery()
        comprometido_fail = db.session.query(func.avg(sub.c.percent)).scalar()
        comprometido_fail = 0 if comprometido_fail is None else round(comprometido_fail, 2)
        return comprometido_fail

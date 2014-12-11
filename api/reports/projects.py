# -*- coding: utf-8 -*-
from model import app, db
from model import Project, Invest, Blog, Post, Message

from flask import abort, jsonify
from flask.ext.restful import Resource, reqparse, fields, marshal
from flask.ext.sqlalchemy import sqlalchemy
from flask_restful_swagger import swagger

from sqlalchemy import and_, or_, desc


@swagger.model
class ProjectsResponse:

    __name__ = "ProjectsResponse"

    resource_fields = {
        "failed": fields.Integer,
        "published": fields.Integer,
        "received": fields.Integer,
        "succesful": fields.Integer,
        "successful-percentage": fields.Float,
        "successful-finished": fields.Integer,
        "successful-finished-perc": fields.Float,
        "average-success-percentage": fields.Float,
        "top10-investors": fields.List,
        "top10-collaborations": fields.List,
        "top10-invests": fields.List,
        "top10-fastest": fields.List,
        "average-successful-posts": fields.Float,
    }

    required = resource_fields.keys()


@swagger.model
class ProjectsAPI(Resource):

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('from_date', type=str)
        self.reqparse.add_argument('to_date', type=str)
        self.reqparse.add_argument('node', type=str, action='append')
        self.reqparse.add_argument('project', type=str, action='append')
        self.reqparse.add_argument('category', type=str, action='append')
        super(ProjectsAPI, self).__init__()

    invalid_input = {
        "code": 400,
        "message": "Invalid parameters"
    }

    @swagger.operation(
    summary='Projects report',
    notes='Projects report',
    responseClass='ProjectsResponse',
    nickname='projects',
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
            "description": 'Filter by project categories separated by commas',
            "required": False,
            "dataType": "string"
        }

    ],
    responseMessages=[invalid_input])
    def get(self):
        """Get the Projects Report

        Descripción de los valores devueltos:
        <strong>failed</strong>: Proyectos fallidos
        <strong>published</strong>: Proyectos publicados
        <strong>received</strong>: Proyectos recibidos (enviados a revisión)
        <strong>succesful</strong>: Proyectos exitosos (alcanzaron el mínimo)
        <strong>successful-percentage</strong>: % de proyectos exitosos
        <strong>successful-finished</strong>: Número de proyectos exitosos con campaña finalizada
        <strong>successful-finished-perc</strong>: % éxito campañas finalizadas
        <strong>top10-collaborations</strong>: Las 10 campañas con más colaboraciones
        <strong>top10-investors</strong>: Las 10 campañas con más cofinanciadores
        <strong>top10-invests</strong>: Las 10 campañas que han recaudado más dinero
        <strong>average-success-percentage</strong>: % de recaudación media conseguida por proyectos exitosos
        <strong>top10-fastest</strong>: Las 10 campañas más rápidas en conseguir el mínimo
        <strong>average-successful-posts</strong>: Media de posts en proyectos exitosos

        Además se añade el campo "filters"
        """
        func = sqlalchemy.func
        args = self.reqparse.parse_args()

        filters = []
        # FIXME: Qué fechas coger depende del dato: creación, finalización...
        if args['from_date']:
            filters.append(Invest.date_invested >= args['from_date'])
        if args['to_date']:
            filters.append(Invest.date_invested <= args['to_date'])
        if args['project']:
            filters.append(Invest.project.in_(args['project'][0]))
        if args['node']:
            #
            filters.append(Project.node.in_(args['node']))
            #
            #filters.append(Project.id == InvestNode.project_id)
            #filters.append(InvestNode.project_node.in_(args['node']))
        if args['category']:
            pass

        # - Proyectos enviados a revisión (renombrar Proyectos recibidos)
        f_rev_projects = list(filters)
        f_rev_projects.append(Project.date_updated != None)
        f_rev_projects.append(Project.date_updated != '0000-00-00')
        rev_projects = db.session.query(func.count(Project.id)).filter(*f_rev_projects).scalar()

        # - Proyectos publicados
        f_pub_projects = list(filters)
        f_pub_projects.append(Project.date_published != None)
        f_pub_projects.append(Project.date_published != '0000-00-00')
        f_pub_projects.append(Project.status > 0)
        pub_projects = db.session.query(func.count(Project.id)).filter(*f_pub_projects).scalar()

        # - Proyectos exitosos (llegan al mínimo pueden estar en campaña)
        # FIXME: (Project.status > 0)
        f_succ_projects = list(filters)
        f_succ_projects.append(Project.date_passed != None)
        f_succ_projects.append(Project.date_passed != '0000-00-00')
        #f_succ_projects.append(Project.status.in_([3, 4, 5]))
        f_succ_projects.append(Project.status > 0)
        succ_projects = db.session.query(func.count(Project.id)).filter(*f_succ_projects).scalar()

        # % exito exitosos
        f_pub_projects2 = list(filters)
        f_pub_projects2.append(Project.status > 0)
        and1 = and_(Project.date_passed != None, Project.date_passed != '0000-00-00')
        and2 = and_(Project.date_closed != None, Project.date_closed != '0000-00-00')
        f_pub_projects2.append(or_(and1, and2))
        pub_projects2 = db.session.query(func.count(Project.id)).filter(*f_pub_projects2).scalar()
        if pub_projects2 == 0:
            p_succ_projects = 0
        else:
            p_succ_projects = float(succ_projects) / pub_projects2 * 100
            p_succ_projects = round(p_succ_projects, 2)

        # -(nuevo) proyectos exitosos con campaña finalizada
        # FIXME: correcto?
        f_succ_finished = list(filters)
        f_succ_finished.append(Project.status.in_([4, 5]))
        succ_finished = db.session.query(Project).filter(*f_succ_finished).count()

        # - Proyectos archivados Renombrar por Proyectos Fallidos
        f_fail_projects = list(filters)
        f_fail_projects.append(Project.status == 6)
        fail_projects = db.session.query(func.count(Project.id)).filter(*f_fail_projects).scalar()

        # _(nuevo)% éxito campañas finalizadas
        # FIXME: correcto?
        if succ_finished == 0 and fail_projects == 0:
            p_succ_finished = 0
        else:
            p_succ_finished = float(succ_finished) / (succ_finished + fail_projects)
            p_succ_finished = round(p_succ_finished, 2)

        # - Porcentaje media de recaudación conseguida por proyectos exitosos
        f_p_avg_success = list(filters)
        f_p_avg_success.append(Invest.status.in_([1, 3]))
        f_p_avg_success.append(Project.status.in_([4, 5]))
        p_avg_success = db.session.query(func.sum(Invest.amount) / func.count(func.distinct(Project.id)))\
                                    .join(Project).filter(*f_p_avg_success).scalar()
        if p_avg_success is None:
            p_avg_success = 0
        else:
            p_avg_success = round(p_avg_success, 2)

        # - (NUEVOS)10 Campañas con más cofinanciadores
        # FIXME: invest.status?
        f_top10_investors = list(filters)
        top10_investors = db.session.query(Project.id, func.count(Invest.id).label('total')).join(Invest)\
                                    .filter(*f_top10_investors).group_by(Invest.project)\
                                    .order_by(desc('total')).limit(10).all()

        # - 10 Campañas con más colaboraciones
        # FIXME: correcto?
        f_top10_collaborations = list(filters)
        top10_collaborations = db.session.query(Project.id, func.count(Message.id).label('total')).join(Message)\
                            .filter(*f_top10_collaborations).group_by(Message.project)\
                            .order_by(desc('total')).limit(10).all()

        # - 10 Campañas que han recaudado más dinero
        # FIXME: correcto?
        f_top10_invests = list(filters)
        f_top10_invests.append(Project.status.in_([4, 5]))
        f_top10_invests.append(Invest.status.in_([0, 1, 3]))
        top10_invests = db.session.query(Project.id, func.sum(Invest.amount).label('total')).join(Invest)\
                                    .filter(*f_top10_invests).group_by(Invest.project)\
                                    .order_by(desc('total')).limit(10).all()

        # - Campañas más rápidas en conseguir el mínimo (NUEVO)
        # TODO
        # Contar Invest.date_invested ordenadas que suman Project.minimum. Coger el que tenga menos dias. ¿10?
        # Lo que pasa es que va a haber primero proyectos de poco dinero.
        top10_fastest = 0
        # passed - published
        db.session.query(func.daytime)
        # - Media de posts proyecto exitoso
        f_avg_succ_posts = list(filters)
        f_avg_succ_posts.append(Post.publish == 1)
        sq1 = db.session.query(func.count(Project.id).label('posts')).select_from(Post)\
                            .join(Blog, and_(Blog.id == Post.blog, Blog.type == 'project'))\
                            .join(Project, and_(Project.id == Blog.owner, Project.status.in_([4, 5])))\
                            .filter(*f_avg_succ_posts).group_by(Post.blog).subquery()
        avg_succ_posts = db.session.query(func.avg(sq1.c.posts)).scalar()


        res = {'received': rev_projects, 'published': pub_projects, 'failed': fail_projects,
                'succesful': succ_projects, 'successful-percentage': p_succ_projects,
                'top10-collaborations': top10_collaborations, 'top10-invests': top10_invests,
                'top10-fastest': top10_fastest, 'top10-investors': top10_investors,
                'successful-finished': succ_finished, 'successful-finished-perc': p_succ_finished,
                'average-success-percentage': p_avg_success, 'average-successful-posts': avg_succ_posts
                }

        res['filters'] = {}
        for k, v in args.items():
            if v is not None:
                res['filters'][k] = v

        return jsonify(res)

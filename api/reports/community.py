# -*- coding: utf-8 -*-
from flask.ext.restful import Resource

from model import Invest, User, Category

from flask.ext.sqlalchemy import sqlalchemy


class CommunityAPI(Resource):

    def __init__(self):
        super(CommunityAPI, self).__init__()

    def get(self):

        func = sqlalchemy.func
        # - Número total de usuarios formados en Goteo (num de proyectos enviados a revisión + inscrito talleres )

        # - Número total de usuarios
        users = User.query.count()

        # - Porcentaje (antes numero) de usuarios que se han dado de baja
        # TODO: ??

        # - Número de cofinanciadores
        cofi = db.session.query(func.distinct(Invest.user)).count()

        # - NEW Porcentaje de usuarios cofinanciadores
        users_cofi_perc = cofi * 100 / users  # %

        # - Cofinanciadores que colaboran
        # ??

        # - Multi-Cofinanciadores (a más de 1 proyecto)
        _multicofi = db.session.query(Invest.user).group_by(Invest.user).having(func.count(Invest.user) > 1)
        multicofi = _multicofi.count()

        # - NEW Porcentaje de Multi-Cofinanciadores (a más de 1 proyecto)
        users_multicofi_perc = multicofi * 100 / users  # %

        # - Cofinanciadores usando PayPal
        paypal = Invest.query.filter(Invest.method==Invest.METHOD_PAYPAL).count()

        # - Multi-Cofinanciadores usando PayPal
        paypal_multicofi = _multicofi.filter(Invest.method==Invest.METHOD_PAYPAL)

        # - Número de colaboradores
        # TODO

        # - Media de cofinanciadores por proyecto exitoso
        # Project.status == 6?, Invest.project == Project.id, distinct(user)

        # - Media de colaboradores por proyecto
        # TODO

        # - Núm. impulsores que cofinancian a otros

        # - Núm. impulsores que colaboran con otros

        # - 1ª Categoría con más usuarios interesados
        #Project.category == Category.id
        # Project.category es null o blanco. ¿?

        # - Porcentaje de usuarios en esta 1ª
        # - 2ª Categoría con más usuarios interesados
        # - Porcentaje de usuarios en esta 2ª
        
        # - Top 10 Cofinanciadores (REVISAR como sacamos estos datos, excepto admines)
        # - Top 10 Cofinanciadores con más caudal (más generosos) excluir usuarios convocadores Y ADMINES
        # - Top 10 colaboradores
        pass

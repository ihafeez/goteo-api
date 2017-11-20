# -*- coding: utf-8 -*-

from flask.ext.restful import fields
from flasgger.utils import swag_from
from flask import g, jsonify
from .. import app
from ..ratelimit import ratelimit
from ..base_resources import BaseItem
from .decorators import requires_auth, generate_auth_token

user_resource_fields = {
    "id": fields.String
}


class TokenAPI(BaseItem):
    """Obtain token"""

    @requires_auth(scope='access_token')
    @ratelimit()
    @swag_from('swagger_specs.yml')
    def get(self):
        duration = int(app.config['ACCESS_TOKEN_DURATION'])
        token = generate_auth_token(g.loginId, duration)
        return jsonify({
            'access_token': token.decode('ascii'),
            'expires_in': duration,
            'token_type': 'bearer'
        })

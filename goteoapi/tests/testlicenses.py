# -*- coding: utf-8 -*-
#
# Minimal tests for main routes
#
from nose.tools import *
import os
from . import test_app, check_content_type, get_json, get_swagger
from ..licenses.resources import license_resource_fields

DIR = os.path.dirname(__file__) + '/../licenses/'

def test_licenses():
    fields_swagger = get_swagger(DIR + 'swagger_specs.yml', 'License')
    rv = test_app.get('/licenses/')
    check_content_type(rv.headers)
    resp = get_json(rv)

    fields = license_resource_fields
    if 'time-elapsed' in resp:
        del resp['time-elapsed']

    eq_(len(set(map(lambda x: str(x), resp.keys())) - set(fields.keys())) >= 0, True)
    eq_(rv.status_code, 200)
    # Swagger test
    eq_(set(resp['items'][0].keys()) , set(fields_swagger.keys()))


# -*- coding: utf-8 -*-
#
# Minimal tests for main routes
#
import json
from nose.tools import *

from . import app,test_app, check_content_type
from ..categories.resources import CategoryResponse as Response, CategoriesListResponse as ListResponse

app.config['AUTH_ENABLED'] = False

def test_categories():
    rv = test_app.get('/categories/')
    check_content_type(rv.headers)
    resp = json.loads(rv.data)

    fields = ListResponse.resource_fields
    if 'time-elapsed' in fields:
        del fields['time-elapsed']
    if 'time-elapsed' in resp:
        del resp['time-elapsed']

    eq_(len(set(map(lambda x: str(x), resp.keys())) - set(fields.keys())) >= 0, True)
    eq_(rv.status_code, 200)

# def test_category():
#     rv = test_app.get('/categories/2/')
#     check_content_type(rv.headers)
#     resp = json.loads(rv.data)
#     print resp
#     fields = Response.resource_fields
#     if 'time-elapsed' in fields:
#         del fields['time-elapsed']
#     if 'time-elapsed' in resp:
#         del resp['time-elapsed']

#     eq_(len(set(map(lambda x: str(x), resp.keys())) - set(fields.keys())) >= 0, True)
#     eq_(rv.status_code, 200)


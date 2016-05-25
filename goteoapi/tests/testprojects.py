# -*- coding: utf-8 -*-
#
# Minimal tests for main routes
#
# #########
# !!!!TODO:
# Create custom entries to SQL table in order to do tests!
#
from nose.tools import *
import os
from . import test_app, get_json, get_swagger
from ..projects.resources import project_resource_fields, project_full_resource_fields

DIR = os.path.dirname(__file__) + '/../projects/'

FILTERS = [
'page=0',
'limit=1',
'page=1&limit=1',
'lang=ca&lang=fr',
'category=2',
'node=barcelona&lang=en&lang=ca',
'from_date=2014-01-01',
'to_date=2014-12-31',
'from_date=2014-01-01&to_date=2014-12-31',
'location=41.38879,2.15899,50',
'location=41.38879,2.15899,50&from_date=2014-01-01',
'location=41.38879,2.15899,50&to_date=2014-12-31',
'location=41.38879,2.15899,50&from_date=2014-01-01&to_date=2014-12-31'
]
def test_projects():
    fields_swagger = get_swagger(DIR + 'swagger_specs/project_list.yml', 'Project')
    for f in FILTERS:
        rv = test_app.get('/projects/' , query_string=f)
        eq_(rv.headers['Content-Type'], 'application/json')
        resp = get_json(rv)
        fields = project_resource_fields
        if 'time-elapsed' in resp:
            del resp['time-elapsed']

        eq_(len(set(map(lambda x: str(x), resp.keys())) - set(fields.keys())) >= 0, True)
        eq_(rv.status_code, 200)
        # Swagger test
        eq_(set(resp['items'][0].keys()) , set(fields_swagger.keys()))


def test_project_no_projects():
    rv = test_app.get('/projects/--i-dont-exits--')
    eq_(rv.status_code, 404)
    rv = test_app.get('/projects/', query_string='category=0')
    resp = get_json(rv)
    eq_(rv.status_code, 200)
    assert 'items' in resp
    eq_(resp['items'], [])

def test_project_trailing_slash():
    rv = test_app.get('/projects')
    eq_(rv.status_code, 301)
    assert 'text/html' in rv.headers['Content-Type']
    assert 'location' in rv.headers, "%r not in %r" % ('location', rv.headers)
    assert '/projects/' in rv.headers['Location'], "%r not in %r" % ('/projects/', rv.headers['Location'])
    rv = test_app.get('/projects/test-project/')
    eq_(rv.status_code, 301)
    assert 'text/html' in rv.headers['Content-Type']
    assert 'location' in rv.headers, "%r not in %r" % ('location', rv.headers)
    assert '/projects/test-project' in rv.headers['Location'], "%r not in %r" % ('/projects/test-project', rv.headers['Location'])

def test_project():
    # TODO: generic project here
    rv = test_app.get('/projects/move-commons/')
    eq_(rv.status_code, 301)
    rv = test_app.get('/projects/move-commons')
    eq_(rv.headers['Content-Type'], 'application/json')
    resp = get_json(rv)
    fields = project_full_resource_fields
    if 'time-elapsed' in resp:
        del resp['time-elapsed']

    eq_(len(set(map(lambda x: str(x), resp.keys())) - set(fields.keys())) >= 0, True)
    eq_(rv.status_code, 200)
    # Swagger test
    fields = get_swagger(DIR + 'swagger_specs/project_item.yml', 'ProjectFull')
    eq_(set(resp.keys()) , set(fields.keys()))
    # Swagger subobjects test
    fields = get_swagger(DIR + 'swagger_specs/project_item.yml', 'ProjectReward')
    eq_(set(resp['rewards'].pop(0).keys()) , set(fields.keys()))
    fields = get_swagger(DIR + 'swagger_specs/project_item.yml', 'ProjectCost')
    eq_(set(resp['costs'].pop(0).keys()) , set(fields.keys()))
    fields = get_swagger(DIR + 'swagger_specs/project_item.yml', 'ProjectNeed')
    eq_(set(resp['needs'].pop(0).keys()) , set(fields.keys()))

def test_call_projects():
    fields_swagger = get_swagger(DIR + 'swagger_specs/project_donors.yml', 'ProjectDonor')
    rv = test_app.get('/projects/move-commons/donors')
    eq_(rv.status_code, 301)
    rv = test_app.get('/projects/move-commons/donors/')
    eq_(rv.status_code, 200)
    eq_(rv.headers['Content-Type'], 'application/json')
    resp = get_json(rv)
    fields = project_resource_fields
    if 'time-elapsed' in resp:
        del resp['time-elapsed']

    eq_(len(set(map(lambda x: str(x), resp.keys())) - set(fields.keys())) >= 0, True)

    # Swagger test
    eq_(set(resp['items'][0].keys()) , set(fields_swagger.keys()))

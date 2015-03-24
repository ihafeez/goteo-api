#!/usr/bin/env python
# -*- coding: utf-8 -*-
import flask
from flask import jsonify
from flask_restful_swagger import swagger
from config import config
from api import app

@app.after_request
def add_cors(resp):
    """ Ensure all responses have the CORS headers. This ensures any failures are also accessible
        by the client. """
    resp.headers['Access-Control-Allow-Origin'] = flask.request.headers.get('Origin','*')
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS, GET'
    resp.headers['Access-Control-Allow-Headers'] = flask.request.headers.get('Access-Control-Request-Headers', 'Authorization')
    # set low for debugging
    if app.debug:
        resp.headers['Access-Control-Max-Age'] = '1'
    return resp

@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(410)
@app.errorhandler(500)
def page_not_found(e):
     resp = jsonify(error=e.code, message=str(e), links=config.links)
     resp.status_code = e.code
     return resp

#
# Routing
# =======

# HOME
@app.route('/', endpoint='api_home')
# @requires_auth
# @ratelimit()
def index():
    """API Welcome. All the available endpoints of the API"""

    func_list = {}
    for rule in app.url_map.iter_rules():
        # Filter out rules non Goteo-api rules
        if "GET" in rule.methods and rule.endpoint.startswith('api_'):
            func_list[rule.rule] = app.view_functions[rule.endpoint].__doc__
    return jsonify(version=config.version, message=config.description + ' v' + str(config.version), endpoints=func_list, links=config.links)

#Add modules
from api.reports_endpoint import api_reports
from api.controllers_endpoint import api_users, api_licenses, api_categories, api_digests

app.register_blueprint(api_reports)
app.register_blueprint(api_users)
app.register_blueprint(api_licenses)
app.register_blueprint(api_categories)
app.register_blueprint(api_digests)


#This part will not be executed under uWSGI module (nginx)
if __name__ == '__main__':
    app.debug = True

    if app.debug:
        import os
        module_path = os.path.dirname(swagger.__file__)
        module_path = os.path.join(module_path, 'static')
        extra_dirs = [module_path, ]
        extra_files = extra_dirs[:]
        for extra_dir in extra_dirs:
            for dirname, dirs, files in os.walk(extra_dir):
                for filename in files:
                    filename = os.path.join(dirname, filename)
                    if os.path.isfile(filename):
                        extra_files.append(filename)
    else:
        extra_files = []

    app.run(host='0.0.0.0', extra_files=extra_files)

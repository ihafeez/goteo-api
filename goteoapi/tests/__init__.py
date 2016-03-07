import sys
import json
from .. import app
from nose.tools import eq_

app.config['TESTING'] = True
app.debug = False
app.config['DEBUG'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['CACHING'] = False
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_TIMEOUT'] = 300
app.config['CACHE_KEY_PREFIX'] = 'Test/'
app.config['AUTH_ENABLED'] = False

if '-v' in sys.argv:
    app.debug = True
    app.config['DEBUG'] = True

test_app = app.test_client()

__import__('goteoapi.controllers')


def check_content_type(headers):
  eq_(headers['Content-Type'], 'application/json')

def get_json(rv_object):
  return json.loads(rv_object.get_data(as_text=True))

def get_swagger(file):
    import yaml
    print(file)
    docs = yaml.load_all(open(file, "r"))
    next(docs)
    return next(docs)

# def teardown():
#   # db_session.remove()
#   pass

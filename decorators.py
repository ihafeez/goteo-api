import time
from functools import update_wrapper
from flask import request, g, session

from model import app, redis
from sqlalchemy.orm.exc import NoResultFound


class RateLimit(object):
    expiration_window = 10

    def __init__(self, key_prefix, limit, per, send_x_headers):
        self.reset = (int(time.time()) // per) * per + per
        self.key = key_prefix + str(self.reset)
        self.limit = limit
        self.per = per
        self.send_x_headers = send_x_headers
        p = redis.pipeline()
        p.incr(self.key)
        p.expireat(self.key, self.reset + self.expiration_window)
        self.current = min(p.execute()[0], limit)

    remaining = property(lambda x: x.limit - x.current)
    over_limit = property(lambda x: x.current >= x.limit)

def get_view_rate_limit():
    return getattr(g, '_view_rate_limit', None)

def on_over_limit(limit):
    return 'You hit the rate limit', 400

def ratelimit(limit=300, per=60 * 15, send_x_headers=True, over_limit=on_over_limit):
    def decorator(f):
        def rate_limited(*args, **kwargs):
            #key = 'rate-limit/%s/%s/' % (key_func(), scope_func())
            #print key_func(), scope_func() # community 127.0.0.1
            key = 'rate-limit/%s/' % request.authorization.username
            rlimit = RateLimit(key, limit, per, send_x_headers)
            g._view_rate_limit = rlimit
            if over_limit is not None and rlimit.over_limit:
                return over_limit(rlimit)
            return f(*args, **kwargs)
        return update_wrapper(rate_limited, f)
    return decorator

@app.after_request
def inject_x_rate_headers(response):
    limit = get_view_rate_limit()
    if limit and limit.send_x_headers:
        h = response.headers
        h.add('X-RateLimit-Remaining', str(limit.remaining))
        h.add('X-RateLimit-Limit', str(limit.limit))
        h.add('X-RateLimit-Reset', str(limit.reset))
    return response


######################### auth #########################
# Based on http://flask.pocoo.org/snippets/8/

from functools import wraps
from flask import request, Response
from model import db, UserApi

from datetime import datetime

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if auth:
            try:
                user = db.session.query(UserApi).filter(UserApi.user == auth.username, UserApi.key == auth.password).one()
                if user.expiration_date <= datetime.today():
                    print user.expiration_date, '<=', datetime.today()
                    return Response('You API key has expired!\n')
                return f(*args, **kwargs)
            except NoResultFound:
                """Sends a 401 response that enables basic auth"""
                return Response(
                'You need a key in order to use our API. Please contact us and we will provide you one!\n', 401,
                {'WWW-Authenticate': 'Basic realm="Goteo.org API"'})
        else:
            return Response(
            'You need a key in order to use our API. Please contact us and we will provide you one!\n', 401,
            {'WWW-Authenticate': 'Basic realm="Goteo.org API"'})
    return decorated

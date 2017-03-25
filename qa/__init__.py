from pyramid.config import Configurator
from pymongo import MongoClient

try:
    # for python 2
    from urlparse import urlparse
except ImportError:
    # for python 3
    from urllib.parse import urlparse

def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include('pyramid_chameleon')

    db_url = urlparse(settings['mongo_uri'])
    config.registry.db = MongoClient(
        host=db_url.hostname,
        port=db_url.port,
    )

    def add_db(request):
        db = config.registry.db[db_url.path[1:]]
        return db

    config.add_request_method(add_db, 'db', reify=True)

    config.add_route('hits','/')
    config.scan('.views')
    return config.make_wsgi_app()

import deform
from pymongo import MongoClient
from pyramid.config import Configurator
from pyramid.session import UnencryptedCookieSessionFactoryConfig
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
from .models import Base

try:
    # for python 2
    from urlparse import urlparse
except ImportError:
    # for python 3
    from urllib.parse import urlparse

def main(global_config, **settings):
    session_factory = UnencryptedCookieSessionFactoryConfig('secret')
    config = Configurator(settings=settings,session_factory = session_factory)
    config.include('pyramid_chameleon')
    deform.renderer.configure_zpt_renderer()
    config.add_static_view('static_deform', 'deform:static')

    sqlalchemy_engine = engine_from_config(settings, prefix='sqlalchemy.')
    #Base.metadata.drop_all(sqlalchemy_engine)
    Base.metadata.create_all(sqlalchemy_engine)
    Session = sessionmaker(bind=sqlalchemy_engine)

    def add_db2(request):
        return Session()

    config.add_request_method(add_db2, 'db2', reify=True)
    config.add_route('register','/register')
    config.add_route('login','/login')
    config.add_route('logout','/logout')
    config.add_route('profile','/profile')
    config.add_route('create', '/create/{question_set_id}')
    config.add_route('answer_set', '/set/{question_set_id}/answer')
    config.add_route('report', '/report')
    config.scan('.views')
    config.add_static_view(name='javascript', path='qa:javascript')
    return config.make_wsgi_app()

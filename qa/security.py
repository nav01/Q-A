from pyramid.httpexceptions import HTTPFound, HTTPForbidden

from .models import Topic, QuestionSet, Question

class Session:
    #Authentication
    __LOGGED_IN = 'logged_in'
    __USER = 'user'
    __USER_DB_ID = 'user_db_id'

    #Question Set State
    QUESTION_STATE = 'question_state'

    def login(session,user):
        session[Session.__LOGGED_IN] = True
        session[Session.__USER] = user.username
        session[Session.__USER_DB_ID] = user.id

    def logged_in(session):
        return Session.__LOGGED_IN in session

    def logout(session):
        session.clear()

    def user_id(session):
        return session[Session.__USER_DB_ID]

def requires_logged_in(wrapped):
    def wrapper(context,request):
        if Session.logged_in(request.session):
            return wrapped(context,request)
        else:
            return HTTPFound(request.route_url('login'))
    return wrapper

def requires_not_logged_in(wrapped):
    def wrapper(context,request):
        if not Session.logged_in(request.session):
            return wrapped(context,request)
        else:
            return HTTPFound(request.route_url('profile'))
    return wrapper

def requires_topic_owner(wrapped):
    def wrapper(context, request):
        try:
            user_id = Session.user_id(request.session)
            topic_id = request.matchdict['topic_id']
        except KeyError as _:
            return HTTPForbidden()

        topic = Topic.user_is_owner(user_id, topic_id, request.db2)
        if topic:
            request.topic = topic
            return wrapped(context, request)
        else:
            raise HTTPForbidden()
    return wrapper

def requires_question_set_contributor(wrapped):
    def wrapper(context,request):
        user_id = Session.user_id(request.session)
        set_id = request.matchdict['question_set_id']

        question_set = QuestionSet.user_is_contributor(user_id, set_id, request.db2)
        if question_set:
            request.question_set = question_set
            return wrapped(context, request)
        else:
            raise HTTPForbidden()
    return wrapper

def requires_question_contributor(wrapped):
    def wrapper(context, request):
        user_id = Session.user_id(request.session)
        try:
            set_id = request.matchdict['question_set_id']
            q_type = request.matchdict['type']
            q_id = request.matchdict['question_id']
        except KeyError as _:
            raise HTTPForbidden()

        question = Question.user_is_contributor(user_id, set_id, q_type, q_id, request.db2)
        if question:
            request.question = question
            return wrapped(context, request)
        else:
            raise HTTPForbidden()
    return wrapper

import unittest

from base import DbTestCase, StubUser
from pyramid import testing

class SessionTests(unittest.TestCase):
    def test_login(self):
        from qa.security import Session

        session = {}
        user = StubUser()
        Session.login(session, user)

        self.assertTrue('logged_in' in session)
        self.assertTrue(session['user'] == user.username)
        self.assertTrue(session['user_db_id'] == user.id)

    def test_logged_in(self):
        from qa.security import Session

        session = {'logged_in': True}
        self.assertTrue(Session.logged_in(session))

    def test_logout(self):
        from qa.security import Session

        session = {'logged_in':True}
        Session.logout(session)
        self.assertFalse(Session.logged_in(session))

    def test_user_id(self):
        from qa.security import Session
        session= {'user_db_id': 0}
        self.assertEqual(Session.user_id(session), 0)

class AuthorizationTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        from qa.models import User, Topic, QuestionSet, MultipleChoiceQuestion as MCQ

        self.config = testing.setUp()
        self.config.add_route('login','/login')
        self.config.add_route('profile','/profile')

        self.create_db()
        #Ids are random because they are compared to see whether permission is granted.
        user_id1=5
        user_id2=2
        topic_id=3
        set_id=7
        question_id=16

        self.user = User(id=user_id1,username='test',password='test')
        self.user2 = User(id=user_id2, username='test2',password='test')
        self.topic = Topic(id=topic_id, title='Name', user_id=user_id1)
        self.question_set = QuestionSet(id=set_id, description='Desc', topic_id=topic_id)
        self.mcq = MCQ(**{
            'id':question_id,
            'question_order':1,
            'question_set_id':set_id,
            'description':'Sample',
            'choice_one':'One',
            'choice_two':'Two',
            'choice_three':'Three',
            'choice_four':'Four',
            'correct_answer':1,
        })
        self.db.add_all([self.user, self.user2, self.topic, self.question_set, self.mcq])
        self.db.commit()
        #additional decorators on top of the viewconfig method require the
        #decorator to call a view callable which accepts context and request args.
        self.dummy_view = lambda context, request: True

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    def test_requires_logged_in(self):
        from qa.security import Session, requires_logged_in

        request = testing.DummyRequest()
        decorated_view = requires_logged_in(self.dummy_view)
        self.assertEqual(decorated_view(None,request).location, "http://example.com/login", "Should redirect to login")
        Session.login(request.session,StubUser())
        self.assertTrue(decorated_view(None,request), "Should return self.dummy_view value of True")

    def test_requires_not_logged_in(self):
        from qa.security import Session, requires_not_logged_in

        request = testing.DummyRequest()
        decorated_view = requires_not_logged_in(self.dummy_view)
        self.assertTrue(decorated_view(None,request), "Should return self.dummy_view value of True")

        Session.login(request.session,StubUser())
        self.assertEqual(decorated_view(None,request).location,"http://example.com/profile", "Should redirect to profile.")

    def test_requires_topic_owner(self):
        from qa.security import Session, requires_topic_owner
        from pyramid.httpexceptions import HTTPForbidden

        request = testing.DummyRequest()
        request.db = self.db
        Session.login(request.session, self.user)
        request.matchdict = {'topic_id':self.topic.id}
        decorated_view = requires_topic_owner(self.dummy_view)
        self.assertTrue(decorated_view(None,request), "Should return self.dummy_view value of True")

        Session.login(request.session, self.user2)
        self.assertRaises(HTTPForbidden, decorated_view, None, request)

    def test_requires_question_set_contributor(self):
        from qa.security import Session, requires_question_set_contributor
        from pyramid.httpexceptions import HTTPForbidden

        request = testing.DummyRequest()
        request.db = self.db
        Session.login(request.session, self.user)
        request.matchdict = {'question_set_id':self.question_set.id}
        decorated_view = requires_question_set_contributor(self.dummy_view)
        self.assertTrue(decorated_view(None,request), "Should return self.dummy_view value of True")

        Session.login(request.session, self.user2)
        self.assertRaises(HTTPForbidden, decorated_view, None, request)

    def test_requires_question_contributor(self):
        from qa.security import Session, requires_question_contributor
        from pyramid.httpexceptions import HTTPForbidden

        request = testing.DummyRequest()
        request.db = self.db
        Session.login(request.session, self.user)
        request.matchdict = {'question_set_id':self.question_set.id, 'type': 'mcq', 'question_id': self.mcq.id }
        decorated_view = requires_question_contributor(self.dummy_view)
        self.assertTrue(decorated_view(None,request), "Should return self.dummy_view value of True")

        Session.login(request.session, self.user2)
        self.assertRaises(HTTPForbidden, decorated_view, None, request)

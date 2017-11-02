import unittest

from .models import Base
from pyramid import testing
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

#Test classes which need database access should inherit from this.
class DbTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.sqlalchemy_engine = None
        self.Session = None
        self.db = None

    #Call in the setUp method
    #Adds tables to the database and creates a session.
    def create_db(self):
        self.sqlalchemy_engine = create_engine('postgresql+psycopg2://developer:password@localhost:5432/qa_test', echo=False)
        Base.metadata.create_all(self.sqlalchemy_engine)
        self.Session = sessionmaker(bind=self.sqlalchemy_engine)
        self.db = self.Session()

    #Call in the tearDown method
    #Clears the database of all tables.
    def clear_db(self):
        from . import models
        self.db.close()
        Base.metadata.drop_all(self.sqlalchemy_engine)

class UserViewTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self,*args,**kwargs)

    def setUp(self):
        self.config = testing.setUp()
        self.create_db()
        self.request = testing.DummyRequest()
        self.config.include('pyramid_chameleon')
        self.config.add_route('login','/login')
        self.config.add_route('profile','/profile')

        self.user_key = 'username'
        self.pass_key = 'password'
        self.csrf = 'csrf_token'
        self.submit = 'submit'

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    def test_username_requirements(self):
        from .forms import RegistrationSchema
        from .views import UserViews

        bad_usernames = [
            ('3coolname','Starts with non-letter.'),
            ('_othername','Starts with non-letter.'),
            ('start45' + 'far'*7,'Username too long.'),
            ('st3', 'Username too short.'),
            ('34' + 'cc'*12, 'Starts with number and is too long.'),
            ('3ye', 'Too short and starts with number.')
        ]

        good_usernames = [
            ('yee_supreme','Meets requirements.'),
            ('Y33_Hello','Meets requirements.'),
        ]

        self.request.db2 = self.db
        self.request.method = 'POST'
        self.request.POST = {
            self.submit: self.submit,
            self.csrf: self.request.session.get_csrf_token(),
            self.pass_key : {
                'password': 'G00d_choice',
                'password-confirm': 'G00d_choice'
            },
        }

        for username, fail_message in bad_usernames:
            self.request.POST[self.user_key] = username
            response = UserViews(self.request).register()
            self.assertTrue(RegistrationSchema.USERNAME_REQUIREMENTS_ERROR in response['form'], fail_message)

        for username, fail_message in good_usernames:
            self.request.POST[self.user_key] = username
            response = UserViews(self.request).register()
            self.assertEqual(response.location, "http://example.com/profile", fail_message)

    def test_password_requirements(self):
        from .forms import RegistrationSchema
        from .views import UserViews

        bad_passwords = [
            ("password", "Password cannot be \"password\""),
            ("paSsworD", "Password cannot be \"password\""),
            #One Mistake
            ("dr@g0n_yee", "No uppercase letters."),
            ("DR@G0N_YEE", "No lowercase letters"),
            ("eArthD@y", "No numbers."),
            ("GlUbt0ck", "No symbols."),
            ("@The", "Too short."),
            #Two Mistakes
            ("Word@","Too short, and no numbers."),
            ("wOr3fo", "Too short, no symbols."),
            ("WHAT3&", "Too short, no lower case."),
            ("d@rk30", "Too short, no upper case."),
            ("Treehouse", "No numbers, no symbols."),
            ("TREE.HOUSE@FUN", "No numbers, no lowercase."),
            ("funtime$", "No numbers, no uppercase."),
            ("FAIR3N0UGH", "No symbol, no lowercase."),
            ("fr33bird", "No symbol, no uppercase."),
            ("33@*1(6-+","No uppercase, no lowercase."),
            #Three Mistakes
            ("Word","Short, number, symbol."),
            ("W@W$*","Short, number, lower"),
            ("$pring","Short, number, upper"),
            ("A4","Short, symbol, lower"),
            ("e3g00d","Short, symbol, upper"),
            ("$34%!2","Short, lower, upper"),
            ("GOODTHINGS","Number, symbol, lower"),
            ("seriously","Number, symbol, upper"),
            ("$%*!-+=_&^@#$","Number,lower, upper"),
            ("334890823","Symbol,lower,upper"),
            #Four Mistakes
            ("WHO","Short, number, symbol, lower"),
            ("35792","Short, symbol, lower, upper"),
            ("$!#","Short, number, lower, upper"),
            ("wise","Short, number, symbol, upper"),
        ]
        self.request.method = 'POST'
        self.request.db2 = self.db
        self.request.POST = {
            self.submit: self.submit,
            self.user_key: 'goodUsername',
            self.csrf: self.request.session.get_csrf_token(),
        }
        for password, password_fail_message in bad_passwords:
            #The deform checked password widget expects a dictionary
            self.request.POST[self.pass_key] = {'password':password,'password-confirm':password}
            response = UserViews(self.request).register()
            self.assertTrue(RegistrationSchema.PASSWORD_REQUIREMENTS_ERROR in response['form'], password_fail_message)

        self.request.POST[self.pass_key] = {'password':'$H30g0r@th','password-confirm':'$H30g0r@th'}
        response = UserViews(self.request).register()
        self.assertEqual(response.location,"http://example.com/profile", "Valid password.")

class QuestionViewTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self,*args,**kwargs)

    def setUp(self):
        from .models import User, Topic, QuestionSet, MultipleChoiceQuestion as MCQ
        from .views import Session

        self.config = testing.setUp()
        self.config.add_route('report','/report')
        self.create_db()
        self.request = testing.DummyRequest()
        self.request.db2 = self.db
        self.request.matchdict['question_set_id'] = 1

        self.user = User(id=1, username='user', password='pass')
        self.topic = Topic(id=1,title='Test',user_id=1)
        self.question_set = QuestionSet(id=1,description='Test_Set',topic_id=1)
        self.question = MCQ(
            id=1,
            question_order=1,
            description='@@TestString@@',
            choice_one='a',
            choice_two='b',
            choice_three='c',
            choice_four='d',
            correct_answer=0,
            question_set_id=1,

        )
        self.question2 = MCQ(
            id=2,
            question_order=2,
            description='@@TestString2@@',
            choice_one='a',
            choice_two='b',
            choice_three='c',
            choice_four='d',
            correct_answer=1,
            question_set_id=1,

        )
        self.db.add_all([self.user,self.topic,self.question_set,self.question,self.question2])
        self.db.commit()
        Session.login(self.request.session,self.user)
        self.csrf = 'csrf_token'
        self.submit = 'submit'

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    def test_setup(self):
        from .views import QuestionViews

        self.request.method = 'GET'
        view = QuestionViews(self.request)
        response = view.setup()
        self.assertTrue(self.question.description in response['question_form'])

    def test_answer(self):
        from .views import QuestionViews

        self.request.method='GET'
        view = QuestionViews(self.request)
        response = view.setup()
        self.request.method = 'POST'
        self.request.POST = {'answer':'0', 'submit':None,'csrf_token':self.request.session.get_csrf_token()}
        response = view.answer()
        self.assertTrue(self.question2.description in response['question_form'])

    def test_redirects_to_report_on_empty_question_list(self):
        from .views import QuestionViews

        self.request.method='GET'
        view = QuestionViews(self.request)
        view.setup()
        self.request.method = 'POST'
        self.request.POST = {'answer':'0', 'submit':None,'csrf_token':self.request.session.get_csrf_token()}
        view.answer()
        response = view.answer() #should be at report page now
        self.assertEqual(response.location,"http://example.com/report", "Question Set Exhausted")

class UserTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)
    def setUp(self):
        self.config = testing.setUp()
        self.create_db()

        self.user_key = 'username'
        self.pass_key = 'password'

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    def test_username_already_exists(self):
        from .models import User

        values = {self.user_key:'Fungo', self.pass_key:'test'}#password not relevant for test, but necessary for method
        user = User(**values)
        self.db.add(user)
        self.db.commit()
        self.assertRaises(ValueError, User.create, values, self.db)

    def test_login(self):
        from passlib.hash import pbkdf2_sha256
        from .models import User

        username = 'User1'
        password = 'pass'
        values = {
            self.user_key: username,
            self.pass_key: pbkdf2_sha256.hash(password),
        }
        self.db.add(User(**values))
        self.db.commit()

        #Successful Login
        values[self.pass_key] = password #login expects the unhashed password
        self.assertTrue(User.login(values, self.db), 'Should login successfully.')

        #Non existent user. Bad login.
        values[self.user_key] = 'notuser'
        self.assertFalse(User.login(values, self.db), 'Login should fail.')

        #Correct user, wrong password.
        values[self.user_key] = 'User1'
        values[self.pass_key] = 'wrongpass'
        self.assertFalse(User.login(values, self.db), 'Login should fail.')

class TopicTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        from .models import User

        self.config = testing.setUp()
        self.create_db()
        self.user = User(id=1,username='user', password='password')
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    def test_topic_create(self):
        from .models import Topic
        from sqlalchemy.orm.exc import NoResultFound

        values = {'topics':[{'title': 'Name'}]}
        try:
            Topic.create(self.user.id, values, self.db)
            self.db.query(Topic).filter(Topic.id==1).one()
        except ValueError as e:
            self.fail('Topic creation resulted in unexpected exception being raised.')
        except NoResultFound as e:
            self.fail('Expected topic to exist.')

    def test_topic_create_duplicate_raises_value_error(self):
        from .models import Topic

        values = {'topics':[{'title': 'Name'}]}
        Topic.create(self.user.id, values, self.db)
        self.assertRaises(ValueError, Topic.create, self.user.id, values, self.db)

class QuestionSetTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        from .models import User
        from .models import Topic

        self.config = testing.setUp()
        self.create_db()
        self.user = User(id=1, username='user', password='password')
        self.topic = Topic(id=1, title='Name', user_id=1)
        self.db.add(self.user)
        self.db.add(self.topic)
        self.db.commit()

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    def test_create_question_set(self):
        from .models import QuestionSet
        from sqlalchemy.orm.exc import NoResultFound

        values = {'topic_id':self.topic.id, 'question_sets':[{'description':'Question Set'}]}
        try:
            QuestionSet.create(values, self.db)
            self.db.query(QuestionSet).filter(QuestionSet.id==1).one()
        except ValueError as e:
            self.fail('An exception was raised unexpectedly.')
        except NoResultFound as e:
            self.fail('Expected question set to exist.')

    def test_create_duplicate_question_set_raises_exception(self):
        from .models import QuestionSet

        values = {'topic_id':self.topic.id, 'question_sets':[{'description':'Question Set'}]}
        QuestionSet.create(values, self.db)
        self.assertRaises(ValueError, QuestionSet.create, values, self.db)

class MultipleChoiceQuestionTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        from .models import User
        from .models import Topic
        from .models import QuestionSet

        self.config = testing.setUp()
        self.create_db()
        self.user = User(id=1, username='user', password='password')
        self.topic = Topic(id=1, title='Name', user_id=1)
        self.question_set = QuestionSet(id=1, description='Desc', topic_id=1)
        self.db.add(self.user)
        self.db.add(self.topic)
        self.db.add(self.question_set)
        self.db.commit()
        self.values = {
            'multiple_choice_questions': [
                {
                    'description':'Sample',
                    'choice_one':'One',
                    'choice_two':'Two',
                    'choice_three':'Three',
                    'choice_four':'Four',
                    'correct_answer':1,
                }
            ]
        }

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    def test_create_question(self):
        from .models import MultipleChoiceQuestion as MCQ
        from sqlalchemy.orm.exc import NoResultFound

        try:
            MCQ.create(self.question_set.id, self.values, self.db)
            self.db.query(MCQ).filter(MCQ.id==1).one()
        except ValueError as e:
            self.fail('Unexpected value error was raised')
        except NoResultFound as e:
            self.fail('Expected question to exist.')

    def test_duplicate_question_raises_exception(self):
        from .models import MultipleChoiceQuestion as MCQ

        MCQ.create(self.question_set.id, self.values, self.db)
        self.assertRaises(ValueError, MCQ.create,self.question_set.id, self.values, self.db)

    def test_correct_answer_constraints(self):
        from .models import MultipleChoiceQuestion as MCQ

        self.values['multiple_choice_questions'][0]['correct_answer'] = -1
        self.assertRaises(ValueError, MCQ.create,self.question_set.id, self.values, self.db)

        self.values['multiple_choice_questions'][0]['correct_answer'] = 4
        self.assertRaises(ValueError, MCQ.create,self.question_set.id, self.values, self.db)

class SessionTests(unittest.TestCase):
    def test_login(self):
        from .views import Session

        session = {}
        user = StubUser()
        Session.login(session, user)

        self.assertTrue('logged_in' in session)
        self.assertTrue(session['user'] == user.username)
        self.assertTrue(session['user_db_id'] == user.id)

    def test_logged_in(self):
        from .views import Session

        session = {'logged_in': True}
        self.assertTrue(Session.logged_in(session))

    def test_logout(self):
        from .views import Session

        session = {'logged_in':True}
        Session.logout(session)
        self.assertFalse(Session.logged_in(session))

    def test_user_id(self):
        from .views import Session
        session= {'user_db_id': 0}
        self.assertEqual(Session.user_id(session), 0)

class QuestionSetStateTests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self,*args,**kwargs)
        self.set_id = 0 #arbitrary id, value not relevant to tests

    def test_empty_list_raises_exception(self):
        from .views import QuestionSetState

        questions = []
        self.assertRaises(ValueError, QuestionSetState, questions, self.set_id)

    def test_non_empty_list(self):  #Not sure if necessary presently.
        pass

    def test_current_question(self):
        from .views import QuestionSetState

        questions = [StubQuestion(i) for i in range(0,5)]
        state = QuestionSetState(questions, self.set_id)
        self.assertEqual(state.get_current_question(),state.get_current_question())

    def test_next_question(self):
        from .views import QuestionSetState

        questions = [StubQuestion(i) for i in range(0,5)]
        state = QuestionSetState(questions, self.set_id)
        for i in range(0,len(questions) - 2):
            question = state.get_current_question()
            next_question = state.get_next_question()
            self.assertTrue(next_question.question_order-question.question_order == 1, 'Questions are not one index apart.')

    def test_next_question_returns_none_if_no_more_questions(self):
        from .views import QuestionSetState

        questions = [StubQuestion(0)]
        state = QuestionSetState(questions,self.set_id)
        self.assertEqual(state.get_next_question(), None)

    def test_ready_for_report_true(self):
        from .views import QuestionSetState

        questions = [StubQuestion(i) for i in range(0,3)]
        state = QuestionSetState(questions,self.set_id)
        state.get_next_question()
        state.get_next_question()
        state.get_next_question()
        self.assertTrue(state.ready_for_report())

    def test_ready_for_report_false_still_questions_left(self):
        from .views import QuestionSetState

        questions = [StubQuestion(i) for i in range(0,3)]
        state = QuestionSetState(questions,self.set_id)
        self.assertFalse(state.ready_for_report(), 'There are still questions left to answer.')

    #Not sure how to test this.  Should return a list of tuples and that's all that can really be tested.
    def test_report(self):
        from .views import QuestionSetState

        list_type = [].__class__
        questions = [StubQuestion(0)]
        state = QuestionSetState(questions,self.set_id)
        dummy_answer = 0
        state.record_answer(dummy_answer)
        state.get_next_question()
        report = state.get_report()

        self.assertEqual(list_type, report.__class__, 'Report should return a list.')

#Stub Classes and Methods
class StubQuestion:
    def __init__(self, order):
        self.question_order = order

    def report(self, answer):
        return('','','',True)

class StubUser:
    def __init__(self):
        self.username = 'bob'
        self.id = 1

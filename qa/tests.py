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

        user_id = 1
        self.user = User(id=user_id,username='user', password='password')
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    def test_user_is_owner(self):
        from .models import Topic

        topic_id = 10
        bad_user_id = 99
        bad_topic_id = 33
        topic = Topic(title='Test Title',id=topic_id,user_id=self.user.id)
        self.db.add(topic)
        self.db.commit()

        self.assertTrue(Topic.user_is_owner(self.user.id, topic.id, self.db), 'User is owner.')

        self.assertFalse(Topic.user_is_owner(bad_user_id, topic.id, self.db), 'User is not owner')
        self.assertFalse(Topic.user_is_owner(self.user.id, bad_topic_id, self.db), 'Topic does not exist')
        self.assertFalse(Topic.user_is_owner(bad_user_id, bad_topic_id, self.db ), 'User id is bad and Topic does not exist')

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

    def test_user_delete_cascades(self):
        from .models import Topic

        new_topic = Topic(title='Test', user_id=self.user.id)
        self.db.add(new_topic)
        self.db.commit()
        self.db.delete(self.user)
        self.db.commit()

        self.assertFalse(self.db.query(Topic).filter(Topic.user_id == self.user.id).one_or_none())

    def test_edit_success(self):
        from .models import Topic

        values = {'user_id': self.user.id, 'title': 'Test Title, Please Ignore'}
        topic = Topic(**values)
        self.db.add(topic)
        self.db.commit()

        values['title'] = '_' + values['title']
        topic.edit(values, self.db)
        self.assertEqual(topic.title, values['title'])

    def test_edit_unique_constraint_violation(self):
        from .models import Topic

        values = {'user_id': self.user.id, 'title': 'Test Title, Please Ignore'}
        topic = Topic(**values)
        values['title'] = '_' + values['title']
        topic2 = Topic(**values)
        self.db.add_all([topic, topic2])
        self.db.commit()

        self.assertRaises(ValueError, topic.edit, values, self.db)

class QuestionSetTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        from .models import User
        from .models import Topic

        self.config = testing.setUp()
        self.create_db()

        user_id = 1
        topic_id = 83
        self.user = User(id=user_id, username='user', password='password')
        self.topic = Topic(id=topic_id, title='Name', user_id=user_id)
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

    def test_user_is_contributor(self):
        from .models import QuestionSet

        set_id = 11
        bad_set_id = 35
        user1_id = 1
        user2_id = 2
        self.db.add(QuestionSet(id=set_id,description='Test', topic_id=self.topic.id))
        self.db.commit()

        self.assertTrue(QuestionSet.user_is_contributor(user1_id, set_id, self.db), 'User should have permission!')
        self.assertFalse(QuestionSet.user_is_contributor(user2_id, set_id, self.db), 'User should not have permission!')
        self.assertFalse(QuestionSet.user_is_contributor(user1_id, bad_set_id, self.db), 'User should not have permission! Set does not exist.')

    def test_topic_delete_cascades(self):
        from .models import QuestionSet

        new_question_set = QuestionSet(description='Test', topic_id=self.topic.id)
        self.db.add(new_question_set)
        self.db.commit()
        self.db.delete(self.topic)
        self.db.commit()

        self.assertFalse(self.db.query(QuestionSet).filter(QuestionSet.topic_id == self.topic.id).one_or_none())

    def test_edit_success(self):
        from .models import QuestionSet

        values = {'topic_id':self.topic.id, 'description':'Question Set'}
        question_set = QuestionSet(**values)
        self.db.add(question_set)
        self.db.commit()

        values['description'] = '_' + values['description']
        question_set.edit(values, self.db)
        self.assertEqual(question_set.description, values['description'])

    def test_edit_unique_constraint_violation(self):
        from .models import QuestionSet

        values = {'topic_id':self.topic.id, 'description':'Question Set'}
        question_set = QuestionSet(**values)
        values['description'] = '_' + values['description']
        question_set2 = QuestionSet(**values)
        self.db.add_all([question_set,question_set2])
        self.db.commit()

        self.assertRaises(ValueError, question_set.edit, values, self.db)

class MultipleChoiceQuestionTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        from .models import User
        from .models import Topic
        from .models import QuestionSet

        self.addCleanup(self.clear_db)
        self.config = testing.setUp()
        self.create_db()

        user_id = 4
        topic_id = 9
        set_id = 22
        self.user = User(id=user_id, username='user', password='password')
        self.topic = Topic(id=topic_id, title='Name', user_id=user_id)
        self.question_set = QuestionSet(id=set_id, description='Desc', topic_id=topic_id)
        self.db.add(self.user)
        self.db.add(self.topic)
        self.db.add(self.question_set)
        self.db.commit()
        self.mcq = {
            'description':'Sample',
            'choice_one':'One',
            'choice_two':'Two',
            'choice_three':'Three',
            'choice_four':'Four',
            'correct_answer':1,
        }
        self.values = {
            'multiple_choice_questions': [self.mcq]
        }

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    def test_create_question(self):
        from .models import MultipleChoiceQuestion as MCQ
        from sqlalchemy.orm.exc import NoResultFound

        self.mcq['id'] = 31
        try:
            MCQ.create(self.question_set.id, self.values, self.db)
            self.db.query(MCQ).filter(MCQ.id==self.mcq['id']).one()
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

        below_range_num = -1
        above_range_num = 4
        self.values['multiple_choice_questions'][0]['correct_answer'] = below_range_num
        self.assertRaises(ValueError, MCQ.create,self.question_set.id, self.values, self.db)

        self.values['multiple_choice_questions'][0]['correct_answer'] = above_range_num
        self.assertRaises(ValueError, MCQ.create,self.question_set.id, self.values, self.db)

    def test_user_is_contributor(self):
        from .models import MultipleChoiceQuestion as MCQ, User

        self.mcq['id'] = 19
        bad_question_id = 100
        bad_set_id = 23
        bad_user_id = 5
        MCQ.create(self.question_set.id, self.values, self.db)

        self.assertTrue(MCQ.user_is_contributor(self.user.id, self.question_set.id, self.mcq['id'], self.db), 'User should have permission!')
        self.assertFalse(MCQ.user_is_contributor(self.user.id, self.question_set.id, bad_question_id, self.db), 'User should not have permission because question does not exist!')
        self.assertFalse(MCQ.user_is_contributor(self.user.id, self.question_set.id, bad_set_id, self.db), 'User should not have permission because set does not exist!')
        self.assertFalse(MCQ.user_is_contributor(bad_user_id, self.question_set.id, self.mcq['id'], self.db), 'User should not have permission because user does not exist!')

    def test_edit_success(self):
        from .models import MultipleChoiceQuestion as MCQ

        self.mcq['question_set_id'] = self.question_set.id
        question = MCQ(**self.mcq)
        self.db.add(question)
        self.db.commit()

        new_question_description = '_' + self.mcq['description']
        self.mcq['description'] = new_question_description
        question.edit(self.mcq, self.db)
        self.assertEqual(question.description, new_question_description, 'Description should have changed.')

    def test_edit_unique_constraint_violation(self):
        from .models import MultipleChoiceQuestion as MCQ

        self.mcq['question_set_id'] = self.question_set.id
        question = MCQ(**self.mcq)
        self.mcq['description'] = '_' + self.mcq['description']
        question2 = MCQ(**self.mcq)
        self.db.add_all([question,question2])
        self.db.commit()

        self.assertRaises(ValueError, question.edit, self.mcq, self.db)

    def test_edit_check_constraint_violation(self):
        from .models import MultipleChoiceQuestion as MCQ

        self.mcq['question_set_id'] = self.question_set.id
        question = MCQ(**self.mcq)
        self.db.add(question)
        self.db.commit()

        self.mcq['correct_answer'] = 200
        self.assertRaises(ValueError, question.edit, self.mcq, self.db)

    def test_question_set_delete_cascades(self):
        from .models import MultipleChoiceQuestion as MCQ

        self.mcq['question_set_id'] = self.question_set.id
        new_mcq = MCQ(**self.mcq)
        self.db.add(new_mcq)
        self.db.commit()
        self.db.delete(self.question_set)
        self.db.commit()

        self.assertFalse(self.db.query(MCQ).filter(MCQ.question_set_id == self.question_set.id).one_or_none())

class SessionTests(unittest.TestCase):
    def test_login(self):
        from .security import Session

        session = {}
        user = StubUser()
        Session.login(session, user)

        self.assertTrue('logged_in' in session)
        self.assertTrue(session['user'] == user.username)
        self.assertTrue(session['user_db_id'] == user.id)

    def test_logged_in(self):
        from .security import Session

        session = {'logged_in': True}
        self.assertTrue(Session.logged_in(session))

    def test_logout(self):
        from .security import Session

        session = {'logged_in':True}
        Session.logout(session)
        self.assertFalse(Session.logged_in(session))

    def test_user_id(self):
        from .security import Session
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

class AuthorizationTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        from .models import User, Topic, QuestionSet, MultipleChoiceQuestion as MCQ

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
        from .security import Session, requires_logged_in

        request = testing.DummyRequest()
        decorated_view = requires_logged_in(self.dummy_view)
        self.assertEqual(decorated_view(None,request).location, "http://example.com/login", "Should redirect to login")
        Session.login(request.session,StubUser())
        self.assertTrue(decorated_view(None,request), "Should return self.dummy_view value of True")

    def test_requires_not_logged_in(self):
        from .security import Session, requires_not_logged_in

        request = testing.DummyRequest()
        decorated_view = requires_not_logged_in(self.dummy_view)
        self.assertTrue(decorated_view(None,request), "Should return self.dummy_view value of True")

        Session.login(request.session,StubUser())
        self.assertEqual(decorated_view(None,request).location,"http://example.com/profile", "Should redirect to profile.")

    def test_requires_topic_owner(self):
        from .security import Session, requires_topic_owner
        from pyramid.httpexceptions import HTTPForbidden

        request = testing.DummyRequest()
        request.db2 = self.db
        Session.login(request.session, self.user)
        request.matchdict = {'topic_id':self.topic.id}
        decorated_view = requires_topic_owner(self.dummy_view)
        self.assertTrue(decorated_view(None,request), "Should return self.dummy_view value of True")

        Session.login(request.session, self.user2)
        self.assertRaises(HTTPForbidden, decorated_view, None, request)

    def test_requires_question_set_contributor(self):
        from .security import Session, requires_question_set_contributor
        from pyramid.httpexceptions import HTTPForbidden

        request = testing.DummyRequest()
        request.db2 = self.db
        Session.login(request.session, self.user)
        request.matchdict = {'question_set_id':self.question_set.id}
        decorated_view = requires_question_set_contributor(self.dummy_view)
        self.assertTrue(decorated_view(None,request), "Should return self.dummy_view value of True")

        Session.login(request.session, self.user2)
        self.assertRaises(HTTPForbidden, decorated_view, None, request)

    def test_requires_question_contributor(self):
        from .security import Session, requires_question_contributor
        from pyramid.httpexceptions import HTTPForbidden

        request = testing.DummyRequest()
        request.db2 = self.db
        Session.login(request.session, self.user)
        request.matchdict = {'question_set_id':self.question_set.id, 'type': 'mcq', 'question_id': self.mcq.id }
        decorated_view = requires_question_contributor(self.dummy_view)
        self.assertTrue(decorated_view(None,request), "Should return self.dummy_view value of True")

        Session.login(request.session, self.user2)
        self.assertRaises(HTTPForbidden, decorated_view, None, request)

#Stub Classes and Methods
class StubQuestion:
    def __init__(self, order):
        self.question_order = order

    def report(self, answer):
        return('','','',True)

class StubUser:
    def __init__(self, user_id=1):
        self.username = 'bob'
        self.id = user_id

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

        self.request.db = self.db
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
        self.request.db = self.db
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

    #Related to answering a question set.
    def setUp(self):
        from .models import User, Topic, QuestionSet, MultipleChoiceQuestion as MCQ
        from .views import Session
        from .models import Question
        from .models import QuestionType

        self.addCleanup(self.clear_db)
        self.config = testing.setUp()
        self.config.add_route('report','/report')
        self.create_db()
        self.request = testing.DummyRequest()
        self.request.db = self.db
        self.request.username = 'bob'
        self.request.matchdict['question_set_id'] = 1

        self.user = User(id=1, username='user', password='pass')
        self.topic = Topic(id=1,title='Test',user_id=1)
        self.question_set = QuestionSet(id=1,description='Test_Set',topic_id=1)
        self.request.question_set = self.question_set
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
            type=QuestionType.mcq,
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
            type=QuestionType.mcq,
        )
        self.db.add_all([self.user,self.topic,self.question_set,self.question,self.question2])
        self.db.commit()
        Session.login(self.request.session,self.user)
        self.csrf = 'csrf_token'
        self.submit = 'submit'

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    #Test that the questions are properly set up by verifying that the question
    #description is present in the form.
    def test_setup(self):
        from .views import QuestionViews

        self.request.method = 'GET'
        view = QuestionViews(self.request)
        response = view.setup()
        self.assertTrue(self.question.description in response['question_form'])

    #Test that, upon answering a question, the next one is presented by checking
    #that the description is present in the form.
    def test_answer(self):
        from .views import QuestionViews

        self.request.method='GET'
        view = QuestionViews(self.request)
        response = view.setup()
        self.request.method = 'POST'
        self.request.POST = {'answer':'0', 'submit':None,'csrf_token':self.request.session.get_csrf_token()}
        response = view.answer()
        self.assertTrue(self.question2.description in response['question_form'])

    #Test that, when a question set is exhausted (by answering it), that the user
    #is on the report page.
    def test_redirects_to_report_on_empty_question_list(self):
        from .views import QuestionViews

        self.request.method='GET'
        self.request.username = 'bob'
        view = QuestionViews(self.request)
        view.setup()
        self.request.method = 'POST'
        self.request.POST = {'answer':'0', 'submit':None,'csrf_token':self.request.session.get_csrf_token()}
        view.answer()
        response = view.answer() #should be at report page now
        self.assertEqual(response.location,"http://example.com/report", "Question Set Exhausted")

#Test the User class from models.py
class UserTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        self.addCleanup(self.clear_db)
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

#Test the Topic class from models.py
class TopicTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        from .models import User

        self.addCleanup(self.clear_db)
        self.config = testing.setUp()
        self.create_db()

        user_id = 1
        self.user = User(id=user_id,username='user', password='password')
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    #Test whether the user is the owner (the one who created it).
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
        from sqlalchemy.exc import IntegrityError

        topic1 =  Topic(user_id=self.user.id, title='a')
        topic2 =  Topic(user_id=self.user.id, title='a')
        self.db.add_all([topic1, topic2])
        try:
            self.db.commit()
            self.fail('Expected IntegrityError to be thrown')
        except IntegrityError as e:
            self.assertEqual(e.orig.diag.constraint_name, 'unique_topic_per_user')

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


#Test the QuestionSet class from models.py
class QuestionSetTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        from .models import User
        from .models import Topic

        self.addCleanup(self.clear_db)
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

    #Test that QuestionSet.create works by creating a question and then  querying
    #for it to see that it was successfully added.
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

    #Test that creating a duplicate question set (description) raises an exception
    #by creating a question set and then trying to create it again.
    def test_unique_description_per_topic(self):
        from .models import QuestionSet
        from sqlalchemy.exc import IntegrityError

        question_set1 =  QuestionSet(topic_id=self.topic.id, description='a')
        question_set2 =  QuestionSet(topic_id=self.topic.id, description='a')
        self.db.add_all([question_set1, question_set2])
        try:
            self.db.commit()
            self.fail('Expected IntegrityError to be thrown')
        except IntegrityError as e:
            self.assertEqual(e.orig.diag.constraint_name, 'unique_description_per_topic')

    #Test that a user is a contributor (and therefore has permissions) to a question set.
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

    def test_edit(self):
        from .models import QuestionSet

        values = {'topic_id':self.topic.id, 'description':'Question Set'}
        question_set = QuestionSet(**values)
        self.db.add(question_set)
        self.db.commit()

        values['description'] = '_' + values['description']
        question_set.edit(values, self.db)
        self.assertEqual(question_set.description, values['description'])

    #Test that questions are retrieved by their question order numbers (ascending)
    #by creating questions (out of order for good measure), retrieving them, and
    #then checking the order against a manually ordered list of the questions.
    def test_get_questions(self):
        from .models import Question
        from .models import QuestionType
        from .models import QuestionSet

        values = {'topic_id':self.topic.id, 'description':'Question Set'}
        question_set = QuestionSet(**values)
        self.db.add(question_set)
        self.db.commit()
        #Check empty case
        self.assertEqual([], question_set.get_questions(self.db))

        #Make sure order_by question_order is present and working properly.
        question1 = Question(id=1, question_set_id=question_set.id, description='test1', question_order=1)
        question3 = Question(id=2, question_set_id=question_set.id, description='test2', question_order=9)
        question5 = Question(id=3, question_set_id=question_set.id, description='test3', question_order=11)
        question2 = Question(id=4, question_set_id=question_set.id, description='test4', question_order=4)
        question4 = Question(id=5, question_set_id=question_set.id, description='test5', question_order=10)

        self.db.add_all([question1, question3, question5, question2, question4])
        self.db.commit()
        ordered_questions = [question1,question2,question3,question4,question5]
        self.assertEqual(ordered_questions, question_set.get_questions(self.db))

    #Test reordering of questions.  The constraint which maintains uniqueness in
    #order number should be deferred.
    def test_reorder(self):
        from .models import QuestionSet
        from .models import Question
        from .models import QuestionType

        values = {'topic_id':self.topic.id, 'description':'Question Set'}
        question_set = QuestionSet(**values)
        self.db.add(question_set)
        self.db.commit()
        question1 = Question(id=1, question_set_id=question_set.id, description='test1', question_order=0)
        question2 = Question(id=2, question_set_id=question_set.id, description='test2', question_order=1)
        self.db.add_all([question1,question2])
        self.db.commit()
        try:
            question_set.reorder([2,1], self.db)
        except Exception as e:
            self.fail('Unique constraint unique_order_per_set was not deferred.')
        self.assertTrue(question1.question_order == 1 and question2.question_order == 0)

    #Test that the order of the last question in the set is properly obtained. This
    #number is used in question creation.  When no questions are in the set, it should
    #return -1.
    def test_last_question_order(self):
        from .models import QuestionSet
        from .models import Question
        from .models import QuestionType

        values = {'topic_id':self.topic.id, 'description':'Question Set'}
        question_set = QuestionSet(**values)
        self.db.add(question_set)
        self.db.commit()
        #test default value if no quetsions in set
        self.assertEqual(-1, QuestionSet.last_question_order(question_set.id, self.db))

        question1 = Question(id=1, question_set_id=question_set.id, description='test1', question_order=0)
        self.db.add(question1)
        self.db.commit()
        self.assertEqual(0, QuestionSet.last_question_order(question_set.id, self.db))

class QuestionTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        from .models import User
        from .models import Topic
        from .models import QuestionSet

        self.addCleanup(self.clear_db)
        self.config = testing.setUp()
        self.create_db()

        #Arbitrary ids.
        user_id = 4
        topic_id = 9
        set_id = 22
        self.user = User(id=user_id, username='user', password='password')
        self.topic = Topic(id=topic_id, title='Name', user_id=user_id)
        self.question_set = QuestionSet(id=set_id, description='Desc', topic_id=topic_id)
        self.db.add_all([self.user, self.topic, self.question_set])
        self.db.commit()

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    def test_create(self):
        from .models import Question

        question1 = {'description': 'a'}
        question2 = {'description': 'b'}
        values = {
            'type': 'question',
            'questions': [question1, question2],
        }

        Question.create(self.question_set.id, values, self.db)
        questions = self.db.query(Question).all()
        self.assertTrue(questions[0].description == 'a' and questions[0].question_order == 0)
        self.assertTrue(questions[1].description == 'b' and questions[1].question_order == 1)

    def test_edit(self):
        from .models import Question

        question = Question(description='a', question_order=0, question_set_id=self.question_set.id)
        self.db.add(question)
        self.db.commit()

        #Notice, bad attributes shouldn't matter, assuming they somehow make it past
        #form validation.  Only already present attributes will be updated.
        new_values = {'description': 'new_description', 'garble': 5, 'bad_attr': 'bye'}
        question.edit(new_values, self.db)
        self.assertEqual(question.description, 'new_description')


    def test_user_is_contributor(self):
        from .models import Question, QuestionType, User

        question_id = 9
        bad_question_id = 100
        bad_set_id = 23
        bad_user_id = 5
        question = Question(id=question_id, description='Test', question_order=0, question_set_id=self.question_set.id, type=QuestionType.question)
        self.db.add(question)
        self.db.commit

        self.assertTrue(Question.user_is_contributor(self.user.id, self.question_set.id, question_id, self.db), 'User should have permission!')
        self.assertFalse(Question.user_is_contributor(self.user.id, self.question_set.id, bad_question_id, self.db), 'User should not have permission because question does not exist!')
        self.assertFalse(Question.user_is_contributor(self.user.id, self.question_set.id, bad_set_id, self.db), 'User should not have permission because set does not exist!')
        self.assertFalse(Question.user_is_contributor(bad_user_id, self.question_set.id, question_id, self.db), 'User should not have permission because user does not exist!')

    #Tests that questions must have a unique description per set by attempting
    #to create two questions with the same description.
    def test_unique_description_per_set_constraint(self):
        from .models import Question
        from sqlalchemy.exc import IntegrityError

        #description argument is the one of interest
        question1 = Question(description='test', question_order=0, question_set_id=self.question_set.id)
        question2 = Question(description='test', question_order=1, question_set_id=self.question_set.id)
        self.db.add_all([question1, question2])
        try:
            self.db.commit()
            self.fail('Expected IntegrityError to be thrown')
        except IntegrityError as e:
            self.assertEqual(e.orig.diag.constraint_name, 'unique_description_per_set')

    #Tests that no two (or more I suppose) questions belonging to one set can have
    #the same order value.
    def test_unique_order_per_set_constraint(self):
        from .models import Question
        from sqlalchemy.exc import IntegrityError

        #question_order argument is the one of interest
        question1 = Question(description='test', question_order=0, question_set_id=self.question_set.id)
        question2 = Question(description='testtest', question_order=0, question_set_id=self.question_set.id)
        self.db.add_all([question1, question2])
        try:
            self.db.commit()
            self.fail('Expected IntegrityError to be thrown')
        except IntegrityError as e:
            self.assertEqual(e.orig.diag.constraint_name, 'unique_order_per_set')

    #Tests that the appropriate glyphicon (bootstrap) is loaded, based on whether
    #the user's answer is equal to the actual answer.
    def test_report(self):
        from .models import Question
        correct_answer = 0
        wrong_answer = 1
        self.assertTrue('glyphicon-ok' in Question.report('', correct_answer, correct_answer))
        self.assertTrue('glyphicon-remove' in Question.report('', correct_answer, wrong_answer))

    def test_question_set_delete_cascades(self):
        from .models import Question
        from sqlalchemy import inspect
        question = Question(description='a', question_order=0, question_set_id=self.question_set.id)
        self.db.add(question)
        self.db.commit()
        self.db.delete(self.question_set)
        self.db.commit()
        self.assertFalse(self.db.query(Question).filter(Question.question_set_id == self.question_set.id).one_or_none())

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

        #Arbitrary ids.
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
            'type': 'mcq',
            'multiple_choice_questions': [self.mcq]
        }

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    #Test the valid answer range a multiple choice question can have.
    def test_answer_in_range_constraint(self):
        from .models import MultipleChoiceQuestion as MCQ
        from sqlalchemy.exc import IntegrityError

        def test(range_extreme):
            question = MCQ(**self.mcq, question_set_id=self.question_set.id, question_order=0)
            try:
                question.correct_answer = range_extreme
                self.db.add(question)
                self.db.commit()
                self.fail('Expected IntegrityError to be thrown.')
            except IntegrityError as e:
                self.db.rollback()
                self.assertEqual(e.orig.diag.constraint_name, 'answer_in_range')

        below_range_num = -1
        above_range_num = 4
        test(below_range_num)
        test(above_range_num)

    def test_unique_multiple_choices_constraint(self):
        from .models import MultipleChoiceQuestion as MCQ
        from sqlalchemy.exc import IntegrityError

        def test(question):
            try:
                self.db.add(question)
                self.db.commit()
                self.fail('Expected IntegrityError to be thrown.')
            except IntegrityError as e:
                self.db.rollback()
                self.assertEqual(e.orig.diag.constraint_name, 'unique_multiple_choices')

        question = MCQ(description='a', question_set_id=self.question_set.id, question_order=0, correct_answer=0)
        question.choice_one = question.choice_two = question.choice_three = question.choice_four = 'same choice'
        test(question)
        question.choice_one = question.choice_two = question.choice_three = 'same choice 2'
        test(question)
        question.choice_one = question.choice_two = 'same choice 3'
        test(question)

    #Test that deleting the super class (Question) instance of MultipleChoiceQuestion
    #deletes the multiple choice question from the database.
    def test_delete_question_cascades(self):
        from .models import Question, MultipleChoiceQuestion as MCQ
        self.mcq['question_set_id'] = self.question_set.id
        self.mcq['question_order'] = 1
        question = MCQ(**self.mcq)
        self.db.add(question)
        self.db.commit()

        #Get and delete the base instance.
        question_base_instance = self.db.query(Question).filter(Question.id == 1).one_or_none()
        self.db.delete(question_base_instance)
        self.db.commit()
        #Check that the descendant instance's data is no longer in the database.
        self.assertFalse(self.db.query(MCQ).filter(Question.id == question.id).one_or_none())

class TrueFalseQuestionTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        from .models import User
        from .models import Topic
        from .models import QuestionSet

        self.addCleanup(self.clear_db)
        self.config = testing.setUp()
        self.create_db()

        #Arbitrary ids.
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
        self.tf = {
            'description':'Sample',
            'correct_answer':False,
        }
        self.values = {
            'type': 'tf',
            'multiple_choice_questions': [self.tf]
        }

    def tearDown(self):
        self.clear_db()
        testing.tearDown()


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
        request.db = self.db
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
        request.db = self.db
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
        request.db = self.db
        Session.login(request.session, self.user)
        request.matchdict = {'question_set_id':self.question_set.id, 'type': 'mcq', 'question_id': self.mcq.id }
        decorated_view = requires_question_contributor(self.dummy_view)
        self.assertTrue(decorated_view(None,request), "Should return self.dummy_view value of True")

        Session.login(request.session, self.user2)
        self.assertRaises(HTTPForbidden, decorated_view, None, request)

class ReorderResourceFormTests(unittest.TestCase):
    def setUp(self):
        from .forms import ReorderResourceForm

        request = testing.DummyRequest()
        ids=list(range(0,3))
        self.form = ReorderResourceForm(request, ids)
    def test_init(self):
        from .forms import ReorderResourceForm
        request = testing.DummyRequest()
        ids = []
        self.assertRaises(ValueError, ReorderResourceForm, request, ids)
        ids.append(1)
        try:
            ReorderResourceForm(request, ids)
        except ValueError as _:
            self.fail('Non empty list falsely raised exception.')

    def test_validate(self):
        from .forms import ReorderResourceForm

        inputs = [ReorderResourceForm.name_template.format(i) for i in range(0,3)]
        post_data = {
            inputs[0]:0,
            inputs[1]:1,
            inputs[2]:2,
            ReorderResourceForm.csrf_token: self.form.csrf_token,
        }
        try:
            self.form.validate(post_data)
        except ValueError as _:
            self.fail('Expected successful validation.')

        del(post_data[ReorderResourceForm.csrf_token])
        self.assertRaises(ValueError, self.form.validate, post_data)

        post_data[ReorderResourceForm.csrf_token] = self.form.csrf_token
        del(post_data[inputs[0]])
        self.assertRaises(ValueError, self.form.validate, post_data)

        del(post_data[inputs[1]])
        del(post_data[inputs[2]])
        self.assertRaises(ValueError, self.form.validate, post_data)

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

import unittest

from base import DbTestCase, StubUser, StubQuestion
from pyramid import testing

class UserViewTests(DbTestCase):
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
        from qa.forms import RegistrationSchema
        from qa.views import UserViews

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
        from qa.forms import RegistrationSchema
        from qa.views import UserViews

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
    #Related to answering a question set.
    def setUp(self):
        from qa.models import User, Topic, QuestionSet, MultipleChoiceQuestion as MCQ
        from qa.views import Session
        from qa.models import Question
        from qa.models import QuestionType

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
        from qa.views import QuestionViews

        self.request.method = 'GET'
        view = QuestionViews(self.request)
        response = view.setup()
        self.assertTrue(self.question.description in response['question_form'])

    #Test that, upon answering a question, the next one is presented by checking
    #that the description is present in the form.
    def test_answer(self):
        from qa.views import QuestionViews

        self.request.method='GET'
        view = QuestionViews(self.request)
        response = view.setup()
        self.request.method = 'POST'
        self.request.POST = {'answer':{'answer':'0'}, 'submit':None,'csrf_token':self.request.session.get_csrf_token()}
        response = view.answer()
        self.assertTrue(self.question2.description in response['question_form'])

    #Test that, when a question set is exhausted (by answering it), that the user
    #is on the report page.
    def test_redirects_to_report_on_empty_question_list(self):
        from qa.views import QuestionViews

        self.request.method='GET'
        self.request.username = 'bob'
        view = QuestionViews(self.request)
        view.setup()
        self.request.method = 'POST'
        self.request.POST = {'answer':{'answer':'0'}, 'submit':None,'csrf_token':self.request.session.get_csrf_token()}
        view.answer()
        response = view.answer() #should be at report page now
        self.assertEqual(response.location,"http://example.com/report", "Question Set Exhausted")

class QuestionSetStateTests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self,*args,**kwargs)
        self.set_id = 0 #arbitrary id, value not relevant to tests

    def test_empty_list_raises_exception(self):
        from qa.views import QuestionSetState

        questions = []
        self.assertRaises(ValueError, QuestionSetState, questions, self.set_id)

    def test_non_empty_list(self):  #Not sure if necessary presently.
        pass

    def test_current_question(self):
        from qa.views import QuestionSetState

        questions = [StubQuestion(i) for i in range(0,5)]
        state = QuestionSetState(questions, self.set_id)
        self.assertEqual(state.get_current_question(),state.get_current_question())

    def test_next_question(self):
        from qa.views import QuestionSetState

        questions = [StubQuestion(i) for i in range(0,5)]
        state = QuestionSetState(questions, self.set_id)
        for i in range(0,len(questions) - 2):
            question = state.get_current_question()
            next_question = state.get_next_question()
            self.assertTrue(next_question.question_order-question.question_order == 1, 'Questions are not one index apart.')

    def test_next_question_returns_none_if_no_more_questions(self):
        from qa.views import QuestionSetState

        questions = [StubQuestion(0)]
        state = QuestionSetState(questions,self.set_id)
        self.assertEqual(state.get_next_question(), None)

    def test_ready_for_report_true(self):
        from qa.views import QuestionSetState

        questions = [StubQuestion(i) for i in range(0,3)]
        state = QuestionSetState(questions,self.set_id)
        state.get_next_question()
        state.get_next_question()
        state.get_next_question()
        self.assertTrue(state.ready_for_report())

    def test_ready_for_report_false_still_questions_left(self):
        from qa.views import QuestionSetState

        questions = [StubQuestion(i) for i in range(0,3)]
        state = QuestionSetState(questions,self.set_id)
        self.assertFalse(state.ready_for_report(), 'There are still questions left to answer.')

    #Not sure how to test this.  Should return a list of tuples and that's all that can really be tested.
    def test_report(self):
        from qa.views import QuestionSetState

        list_type = [].__class__
        questions = [StubQuestion(0)]
        state = QuestionSetState(questions,self.set_id)
        dummy_answer = 0
        state.record_answer(dummy_answer)
        state.get_next_question()
        report = state.get_report()

        self.assertEqual(list_type, report.__class__, 'Report should return a list.')

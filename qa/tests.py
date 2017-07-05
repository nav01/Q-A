import unittest
from pyramid import testing
from pymongo import MongoClient

try:
    # for python 2
    from urlparse import urlparse
except ImportError:
    # for python 3
    from urllib.parse import urlparse

#Test classes which need database access should inherit from this.
class DbTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        mongo_test_uri = "mongodb://@Localhost:27017/test"
        db_url = urlparse(mongo_test_uri)
        db = MongoClient(
            host=db_url.hostname,
            port=db_url.port,
        )
        self.db = db[db_url.path[1:]]
    #Call in the appropriate method if parent setup/teardown are overriden
    def clear_db(self):
        self.db['users'].delete_many({})

class UserViewTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self,*args,**kwargs)
    def setUp(self):
        self.clear_db()
        self.config = testing.setUp()
    def tearDown(self):
        self.clear_db()
        testing.tearDown()
    def test_password_confirmation(self):
        from .forms import RegistrationSchema
        from .views import UserViews
        from pyramid.response import Response
        request = testing.DummyRequest()
        request.method = 'POST'
        request.db = self.db
        request.POST = {
            'csrf_token':request.session.get_csrf_token(),
            'submit':'submit',
            'username':'user123',
            'password':'Thi$_i$_g00d',
        }

        request.POST['password_confirmation'] = 'Thi$_i$_b@d'
        response = UserViews(request).register()
        self.assertTrue(RegistrationSchema.PASSWORD_MATCH_ERROR in response['form'], 'Passwords do not match')

        request.POST['password_confirmation'] = 'Thi$_i$_g00d'
        response = UserViews(request).register()
        self.assertEqual(response.body,b'OK', 'Passwords match.')

    #username form
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
        request = testing.DummyRequest()
        request.db = self.db
        request.method = 'POST'
        request.POST = {
            'submit':'submit',
            'csrf_token':request.session.get_csrf_token(),
            'password':'G00d_choice',
            'password_confirmation':'G00d_choice',
        }

        for username, fail_message in bad_usernames:
            request.POST['username'] = username
            response = UserViews(request).register()
            self.assertTrue(RegistrationSchema.USERNAME_REQUIREMENTS_ERROR in response['form'], fail_message)
        for username, fail_message in good_usernames:
            request.POST['username'] = username
            response = UserViews(request).register()
            self.assertEqual(response.body, b'OK',fail_message)

    #overkill?
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
        request = testing.DummyRequest()
        request.method = 'POST'
        request.db = self.db
        request.POST = {
            'submit':'submit',
            'username':'goodUsername',
            'csrf_token':request.session.get_csrf_token(),
        }
        for password, password_fail_message in bad_passwords:
            request.POST['password'] = password
            request.POST['password_confirmation'] = password
            response = UserViews(request).register()
            if(request.POST['password'] == ""):
                print(response['form'])
            self.assertTrue(RegistrationSchema.PASSWORD_REQUIREMENTS_ERROR in response['form'], password_fail_message)
        request.POST['password'] = "Sh30g0r@th"
        request.POST['password_confirmation'] = "Sh30g0r@th"
        response = UserViews(request).register()
        self.assertEqual(response.body,b'OK', "Valid password.")

class UserTests(DbTestCase):
    def __init__(self, *args, **kwargs):
        DbTestCase.__init__(self, *args, **kwargs)
    def setUp(self):
        self.clear_db()
        self.config = testing.setUp()
    def tearDown(self):
        self.clear_db()
        testing.tearDown()

    def test_username_already_exists(self):
        from .models import User
        user = {User.USERNAME:"Fungo"}
        self.db['users'].insert_one(user)
        self.assertRaises(ValueError,User.create, user, self.db)

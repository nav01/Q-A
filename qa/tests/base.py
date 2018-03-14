import unittest

from qa.models import Base
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

    def setUp(self):
        self.addCleanup(self.clear_db)
        self.config = testing.setUp()
        self.create_db()

    def tearDown(self):
        self.clear_db()
        testing.tearDown()

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
        from qa import models
        self.db.close()
        Base.metadata.drop_all(self.sqlalchemy_engine)

class QuestionTestCase(DbTestCase):
    def setUp(self):
        from qa.models import (
            User,
            Topic,
            QuestionSet,
            Question,
            MultipleChoiceQuestion,
            TrueFalseQuestion,
            Accuracy,
            MathQuestion,
        )
        super().setUp()

        self.user = User(username='user', password='password')
        self.topic = Topic(title='Name', user_id=1)
        self.question_set = QuestionSet(description='Desc', topic_id=1)
        self.db.add_all([self.user, self.topic, self.question_set])
        self.db.commit()

        self.mcq = {
            'description':'Sample',
            'choice_one':'One',
            'choice_two':'Two',
            'choice_three':'Three',
            'choice_four':'Four',
            'correct_answer':1,
        }

        self.tf = {
            'description':'Sample',
            'correct_answer':False,
        }

        self.mq = {
            'question_order': 0,
            'description': 'test',
            'correct_answer': 10,
            'accuracy': Accuracy.exact,
            'question_set_id': 1,
        }

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

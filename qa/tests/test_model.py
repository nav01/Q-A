from pyramid import testing
from base import DbTestCase, QuestionTestCase

#Test the User class from models.py
class UserTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.user_key = 'username'
        self.pass_key = 'password'

    def test_username_already_exists(self):
        from qa.models import User

        values = {self.user_key:'Fungo', self.pass_key:'test'}#password not relevant for test, but necessary for method
        user = User(**values)
        self.db.add(user)
        self.db.commit()
        self.assertRaises(ValueError, User.create, values, self.db)

    def test_login(self):
        from passlib.hash import pbkdf2_sha256
        from qa.models import User

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
    def setUp(self):
        from qa.models import User

        super().setUp()

        user_id = 1
        self.user = User(id=user_id,username='user', password='password')
        self.db.add(self.user)
        self.db.commit()

    #Test whether the user is the owner (the one who created it).
    def test_user_is_owner(self):
        from qa.models import Topic

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
        from qa.models import Topic
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
        from qa.models import Topic
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
        from qa.models import Topic

        new_topic = Topic(title='Test', user_id=self.user.id)
        self.db.add(new_topic)
        self.db.commit()
        self.db.delete(self.user)
        self.db.commit()

        self.assertFalse(self.db.query(Topic).filter(Topic.user_id == self.user.id).one_or_none())

    def test_edit_success(self):
        from qa.models import Topic

        values = {'user_id': self.user.id, 'title': 'Test Title, Please Ignore'}
        topic = Topic(**values)
        self.db.add(topic)
        self.db.commit()

        values['title'] = '_' + values['title']
        topic.edit(values, self.db)
        self.assertEqual(topic.title, values['title'])

#Test the QuestionSet class from models.py
class QuestionSetTests(DbTestCase):
    def setUp(self):
        from qa.models import User
        from qa.models import Topic

        super().setUp()

        user_id = 1
        topic_id = 83
        self.user = User(id=user_id, username='user', password='password')
        self.topic = Topic(id=topic_id, title='Name', user_id=user_id)
        self.db.add(self.user)
        self.db.add(self.topic)
        self.db.commit()

    #Test that QuestionSet.create works by creating a question and then  querying
    #for it to see that it was successfully added.
    def test_create_question_set(self):
        from qa.models import QuestionSet
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
        from qa.models import QuestionSet
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
        from qa.models import QuestionSet

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
        from qa.models import QuestionSet

        new_question_set = QuestionSet(description='Test', topic_id=self.topic.id)
        self.db.add(new_question_set)
        self.db.commit()
        self.db.delete(self.topic)
        self.db.commit()

        self.assertFalse(self.db.query(QuestionSet).filter(QuestionSet.topic_id == self.topic.id).one_or_none())

    def test_edit(self):
        from qa.models import QuestionSet

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
        from qa.models import Question
        from qa.models import QuestionType
        from qa.models import QuestionSet

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
        from qa.models import QuestionSet
        from qa.models import Question
        from qa.models import QuestionType

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
        from qa.models import QuestionSet
        from qa.models import Question
        from qa.models import QuestionType

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
    def setUp(self):
        from qa.models import User
        from qa.models import Topic
        from qa.models import QuestionSet

        super().setUp()

        #Arbitrary ids.
        user_id = 4
        topic_id = 9
        set_id = 22
        self.user = User(id=user_id, username='user', password='password')
        self.topic = Topic(id=topic_id, title='Name', user_id=user_id)
        self.question_set = QuestionSet(id=set_id, description='Desc', topic_id=topic_id)
        self.db.add_all([self.user, self.topic, self.question_set])
        self.db.commit()

    def test_create(self):
        from qa.models import Question

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
        from qa.models import Question

        question = Question(description='a', question_order=0, question_set_id=self.question_set.id)
        self.db.add(question)
        self.db.commit()

        #Notice, bad attributes shouldn't matter, assuming they somehow make it past
        #form validation.  Only already present attributes will be updated.
        new_values = {'description': 'new_description', 'garble': 5, 'bad_attr': 'bye'}
        question.edit(new_values, self.db)
        self.assertEqual(question.description, 'new_description')


    def test_user_is_contributor(self):
        from qa.models import Question, QuestionType, User

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
        from qa.models import Question
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
        from qa.models import Question
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
        from qa.models import Question

        correct_answer = 0
        wrong_answer = 1
        self.assertTrue('glyphicon-ok' in Question.report('', correct_answer, correct_answer))
        self.assertTrue('glyphicon-remove' in Question.report('', correct_answer, wrong_answer))

    def test_question_set_delete_cascades(self):
        from qa.models import Question
        from sqlalchemy import inspect

        question = Question(description='a', question_order=0, question_set_id=self.question_set.id)
        self.db.add(question)
        self.db.commit()
        self.db.delete(self.question_set)
        self.db.commit()
        self.assertFalse(self.db.query(Question).filter(Question.question_set_id == self.question_set.id).one_or_none())

class MultipleChoiceQuestionTests(QuestionTestCase):
    #Test the valid answer range a multiple choice question can have.
    def test_answer_in_range_constraint(self):
        from qa.models import MultipleChoiceQuestion as MCQ
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
        from qa.models import MultipleChoiceQuestion as MCQ
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
        from qa.models import Question, MultipleChoiceQuestion as MCQ

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
    pass

class MathQuestionTests(QuestionTestCase):
    def test_both_unit_columns_or_neither_constraint(self):
        from qa.models import MathQuestion
        from sqlalchemy.exc import IntegrityError

        question = MathQuestion(**self.mq)

        #neither columns
        try:
            self.db.add(question)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.fail('Both unit fields are empty.  Should succeed.')

        #both columns
        question.units = 'units'
        question.units_given = True
        try:
            self.db.add(question)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.fail('Both unit fields present.  Should succeed.')

        #one unit column missing
        question.units = None
        try:
            self.db.add(question)
            self.db.commit()
            self.fail('Expected IntegrityError to be thrown.')
        except IntegrityError as e:
            self.assertEqual(e.orig.diag.constraint_name, 'both_unit_columns_or_neither')

    def test_accuracy_degree_must_be_specified_if_not_exact_constraint(self):
        from qa.models import Accuracy, MathQuestion
        from sqlalchemy.exc import IntegrityError

        question = MathQuestion(**self.mq)

        #specifying accuracy_degree when accuracy is exact
        question.accuracy_degree = 5
        try:
            self.db.add(question)
            self.db.commit()
            self.fail('Expected IntegrityError to be raised.')
        except IntegrityError as e:
            self.db.rollback()
            self.assertEqual(e.orig.diag.constraint_name, 'accuracy_degree_must_be_specified_if_not_exact')

        #both columns present
        question.accuracy = Accuracy.uncertainty
        try:
            self.db.add(question)
            self.db.commit()
        except Exception as e:
            self.fail('Both accuracy (not exact) and degree are specified.  Should succeed.')

        #degree not present
        question.accuracy_degree = None
        try:
            self.db.add(question)
            self.db.commit()
            self.fail('Expected IntegrityError to be raised.')
        except IntegrityError as e:
            self.db.rollback()
            self.assertEqual(e.orig.diag.constraint_name, 'accuracy_degree_must_be_specified_if_not_exact')

    def test_compare_to_answer_for_report(self):
        from qa.models import Accuracy, MathQuestion

        question = MathQuestion(**self.mq)

        #exact accuracy
        self.assertTrue(question._compare_to_answer_for_report({'answer': question.correct_answer})[0])
        self.assertFalse(question._compare_to_answer_for_report({'answer': 1})[0])

        #uncertainty
        question.accuracy = Accuracy.uncertainty
        question.correct_answer = 100 #answer explicit for clarity
        question.accuracy_degree = 5
        self.assertTrue(question._compare_to_answer_for_report({'answer': question.correct_answer})[0])
        self.assertTrue(question._compare_to_answer_for_report({'answer': question.correct_answer + question.accuracy_degree})[0])
        self.assertTrue(question._compare_to_answer_for_report({'answer': question.correct_answer - question.accuracy_degree})[0])
        self.assertTrue(question._compare_to_answer_for_report({'answer': question.correct_answer + question.accuracy_degree - 2})[0])
        self.assertTrue(question._compare_to_answer_for_report({'answer': question.correct_answer - question.accuracy_degree + 2})[0])
        self.assertFalse(question._compare_to_answer_for_report({'answer': question.correct_answer + question.accuracy_degree + .01})[0])
        self.assertFalse(question._compare_to_answer_for_report({'answer': question.correct_answer - question.accuracy_degree - .01})[0])

        #percentage
        question.accuracy = Accuracy.percentage
        question.correct_answer = 10 #make answer explicit here for clarity
        question.accuracy_degree = 10
        self.assertTrue(question._compare_to_answer_for_report({'answer': question.correct_answer})[0])
        self.assertTrue(question._compare_to_answer_for_report({'answer': question.correct_answer + 1})[0])
        self.assertTrue(question._compare_to_answer_for_report({'answer': question.correct_answer - 1})[0])
        self.assertTrue(question._compare_to_answer_for_report({'answer': question.correct_answer + 0.5})[0])
        self.assertTrue(question._compare_to_answer_for_report({'answer': question.correct_answer + 0.5})[0])
        self.assertFalse(question._compare_to_answer_for_report({'answer': question.correct_answer + 1.01})[0])
        self.assertFalse(question._compare_to_answer_for_report({'answer': question.correct_answer - 1.01})[0])

import enum

from passlib.hash import pbkdf2_sha256
from psycopg2 import errorcodes
from sqlalchemy import (
    Column, Integer, String, Boolean, Enum, Float, ForeignKey,
    event,
    CheckConstraint, UniqueConstraint,
    func,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, with_polymorphic
from sqlalchemy.orm.exc import NoResultFound

#There are imports at the method level of classes that have corresponding forms.
#This is to resolve an issue with cyclic imports between the forms and models modules.
#The reason for cyclic imports is so that the form fields can use database column names
#to reduce additional processing when going from form to model instance.
#TODO Solve cyclic import issue.
Base = declarative_base()

class User(Base):
    #sql variables
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(25), nullable=False, unique=True)
    password = Column(String, nullable=False)

    topics =  relationship('Topic', back_populates='user', passive_deletes='all')

    def create(values, db):
        try:
            password_hash = pbkdf2_sha256.hash(values[User.password.name])
            user = User(username=values[User.username.name], password=password_hash)
            db.add(user)
            db.commit()
            return user
        except IntegrityError as e:
            db.rollback
            if e.orig.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise ValueError('Username is taken.')

    def login(values, db):
        user =  db.query(User).filter(User.username==values[User.username.name]).first()
        if user and pbkdf2_sha256.verify(values[User.password.name], user.password):
            return user
        else:
            return None

    #Gets the User object associated with the user_id.  Assumes user exists.
    def get_user(user_id, db):
        return db.query(User).filter(User.id==user_id).first()

class Topic(Base):
    __tablename__='topics'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='cascade'), nullable=False)

    user = relationship('User', back_populates='topics')
    question_sets = relationship('QuestionSet', back_populates='topic', passive_deletes='all')

    __table_args__ = (
        UniqueConstraint('title','user_id', name='unique_topic_per_user'),
    )

    def user_is_owner(user_id, topic_id, db):
        try:
            topic = db.query(Topic).\
                join(User).\
                filter(Topic.id == topic_id, Topic.user_id == user_id).one()
            return topic
        except NoResultFound as _:
            return False

    def create(user_id, values, db):
        try:
            new_topics = [Topic(user_id=user_id, title=value[Topic.title.name]) for value in values[Topic.__table__.name]]
            db.add_all(new_topics)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            if e.orig.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise ValueError('Some submitted topic(s) are duplicates.')
            elif e.orig.pgcode == errorcodes.NOT_NULL_VIOLATION:
                raise ValueError('A topic title cannot be empty.')

    def edit(self, new_values, db):
        try:
            #Said to be a slow method to update via dictionary, but can't find anything better right now.
            for key, value in new_values.items():
                setattr(self, key, value)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            if e.orig.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise ValueError('A topic with that title exists already.')

    def edit_schema(self):
        from .forms import CSRFSchema, Topic, merge_schemas

        csrf_schema = CSRFSchema()
        topic_schema = Topic()
        merge_schemas(csrf_schema, topic_schema)
        return csrf_schema

class QuestionSet(Base):
    __tablename__='question_sets'

    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    topic_id = Column(Integer, ForeignKey('topics.id', ondelete='cascade'), nullable=False)

    topic = relationship('Topic', back_populates='question_sets')
    questions = relationship('Question', back_populates='question_set', passive_deletes='all', order_by='Question.question_order')

    __table_args__ = (
        UniqueConstraint('topic_id', 'description', name='unique_description_per_topic'),
    )

    def user_is_contributor(user_id, question_set_id, db):
        try:
            question_set = db.query(QuestionSet).\
                join(Topic).\
                join(User).\
                filter(QuestionSet.id == question_set_id, User.id == user_id).one()
            return question_set
        except NoResultFound as _:
            return False

    def create(values, db):
        try:
            new_question_sets = [QuestionSet(topic_id=values[QuestionSet.topic_id.name],description=value[QuestionSet.description.name]) for value in values[QuestionSet.__table__.name]]
            db.add_all(new_question_sets)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            if e.orig.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise ValueError('Some question set(s) exist already.')
            elif e.orig.pgcode == errorcodes.NOT_NULL_VIOLATION:
                raise ValueError('Some necessary field was left blank.')

    def edit(self, new_values, db):
        try:
            #Said to be a slow method to update via dictionary, but can't find anything better right now.
            for key, value in new_values.items():
                setattr(self, key, value)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            if e.orig.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise ValueError('A question set with that description exists already.')

    def edit_schema(self):
        from .forms import CSRFSchema, QuestionSet, merge_schemas

        csrf_schema = CSRFSchema()
        question_set_schema = QuestionSet()
        merge_schemas(csrf_schema, question_set_schema)
        return csrf_schema

    def reorder(self, new_order, db):
        order = [{'id':i, 'question_order': index} for index, i in enumerate(new_order)]
        db.execute('SET CONSTRAINTS unique_order_per_set DEFERRED;')
        db.bulk_update_mappings(Question, order)
        db.commit()

    def get_questions(self, db):
        questions = db.query(Question.LOAD_COMPLETE_POLYMORPHIC_RELATION).\
            join(QuestionSet).\
            filter(Question.question_set_id == self.id).\
            order_by(Question.LOAD_COMPLETE_POLYMORPHIC_RELATION.question_order).all()
        return questions

    def last_question_order(question_set_id, db):
        return db.query(func.coalesce(func.max(Question.question_order), -1)).filter(Question.question_set_id == question_set_id).scalar()

class QuestionType(enum.Enum):
    question = 1
    mcq = 2 #multiple choice question
    tf = 3 #true/false
    math = 4

    @classmethod
    def get_question_class(cls, question_type):
        if question_type == cls.mcq.name:
            return MultipleChoiceQuestion
        elif question_type == cls.tf.name:
            return TrueFalseQuestion
        elif question_type == cls.math.name:
            return MathQuestion
        elif question_type == cls.question.name:
            return Question

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    type = Column(Enum(QuestionType), nullable=False)
    description = Column(String, nullable=False)
    question_order = Column(Integer, nullable=False)
    question_set_id = Column(Integer, ForeignKey('question_sets.id', ondelete='cascade'), nullable=False)

    question_set = relationship('QuestionSet', back_populates='questions')

    __table_args__ = (
        UniqueConstraint('question_set_id', 'description', name='unique_description_per_set'),
        UniqueConstraint('question_set_id', 'question_order', name='unique_order_per_set', deferrable=True)
    )
    __mapper_args__ = {
        'polymorphic_identity': QuestionType.question,
        'polymorphic_on': type,
    }

    REPORT_TEMPLATE = '''
        <h4>{} <i class="glyphicon glyphicon {}"></i></h4>
        <p>Correct Answer: {}</p>
        <p>Your Answer: {}</p>
    '''

    @classmethod
    def report(cls, description, correct_answer, chosen_answer):
        t = cls.REPORT_TEMPLATE.format(
            description,
            {},
            correct_answer,
            chosen_answer,
        )
        if chosen_answer == correct_answer:
            return t.format('glyphicon-ok')
        else:
            return t.format('glyphicon-remove')

    @classmethod
    def create(cls, question_set_id, values, db):
        from .forms import FormError

        try:
            q_type = values[cls.type.name]
            Q_class = QuestionType.get_question_class(q_type)
            order_start = QuestionSet.last_question_order(question_set_id, db) + 1
            new_questions = [Q_class(question_set_id=question_set_id, question_order=order_start + i, **value)
                for i, value in enumerate(values[Q_class.__table__.name])]
            db.add_all(new_questions)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise cls.handle_db_exception(e, Q_class)
        except Exception as e:
            raise FormError()

    #Should be an appropriate method for editing all question types, even multipart questions that are yet to be implemented.
    #However, it accesses variables in the child class, though not directly because of the setattr use, which seems like
    #a violation of inheritance.  On the other hand, I would just be writing methods in the child class that will end up
    #consisting of just this function call.
    def edit(self, new_values, db):
        from .forms import FormError

        try:
            #Said to be a slow method to update via dictionary, but can't find anything better right now.
            for key, value in new_values.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise Question.handle_db_exception(e, QuestionType.get_question_class(self.type.name))
        except Exception as _:
            raise FormError()

    def edit_schema(self):
        from .forms import CSRFSchema, get_question_edit_schema, merge_schemas

        csrf_schema = CSRFSchema()
        edit_schema =  get_question_edit_schema(self.type)
        merge_schemas(csrf_schema, edit_schema)
        return csrf_schema

    def user_is_contributor(user_id, question_set_id, question_id, db):
        try:
            question = db.query(Question.LOAD_COMPLETE_POLYMORPHIC_RELATION).\
                join(QuestionSet).\
                join(Topic).\
                join(User).\
                filter(Question.id == question_id, QuestionSet.id == question_set_id, User.id == user_id).one()
            return question
        except NoResultFound as _:
            return False

    def handle_db_exception(e, Q_class):
        if e.orig.pgcode == errorcodes.NOT_NULL_VIOLATION:
            raise ValueError('A required value is missing.')
        elif e.orig.diag.constraint_name == 'unique_description_per_set':
            raise ValueError('Questions must be unique per set.')
        elif e.orig.diag.constraint_name == 'unique_order_per_set':
            raise ValueError('Questions in a set must have a unique order.')
        else:
            raise Q_class.handle_db_exception(e)

class Accuracy(enum.Enum):
    exact = 1
    uncertainty = 2
    percentage = 3

class MathQuestion(Question):
    __tablename__ = 'math_questions'

    id = Column(Integer, ForeignKey('questions.id', ondelete='cascade'), primary_key=True)
    correct_answer = Column(Float, nullable=False)
    units = Column(String(10), nullable=True)
    units_given = Column(Boolean, nullable=True)
    accuracy = Column(Enum(Accuracy), nullable=False)
    accuracy_degree = Column(Float, nullable=True)

    __table_args__ = (
        CheckConstraint(
            """
                units IS NULL AND units_given IS NULL OR
                units IS NOT NULL AND units_given IS NOT NULL
            """,
            name='both_unit_columns_or_neither',
        ),
        CheckConstraint(
            """
                accuracy = 'exact' AND accuracy_degree IS NULL OR
                accuracy IS NOT NULL AND accuracy != 'exact' AND accuracy_degree IS NOT NULL
            """,
            name='accuracy_degree_must_be_specified_if_not_exact',
        )
    )
    __mapper_args__ = {
        'polymorphic_identity': QuestionType.math,
    }

    def answer_schema(self, request):
        from .forms import MathAnswer

        schema = MathAnswer().bind(request=request, question=self)
        return schema

    def _compare_to_answer_for_report(self, answer):
        a = answer['answer']
        if self.accuracy == Accuracy.exact:
            numerically_correct = self.correct_answer == a
        elif self.accuracy == Accuracy.uncertainty:
            numerically_correct = a >= self.correct_answer - self.accuracy_degree and \
                a <= self.correct_answer + self.accuracy_degree
        elif self.accuracy == Accuracy.percentage:
            numerically_correct = a >= self.correct_answer * (1 - self.accuracy_degree / 100.0) and \
                a <= self.correct_answer * (1 + self.accuracy_degree / 100.0)
        if 'units' in answer:
            return (
                self.units.lower() == answer['units'].lower() and numerically_correct,
                str(self.correct_answer) + ' ' + self.units,
                str(a) + ' ' + answer['units'],
            )
        else:
            return (numerically_correct, self.correct_answer, a)

    def report(self, answer):
        answer_is_correct = self._compare_to_answer_for_report(answer)
        report = self.__class__.REPORT_TEMPLATE.format(self.description, {}, answer_is_correct[1], answer_is_correct[2])
        if answer_is_correct[0]:
            return report.format('glyphicon-ok')
        else:
            return report.format('glyphicon-remove')

    def handle_db_exception(e):
        if e.orig.diag.constraint_name == 'both_unit_columns_or_neither':
            raise ValueError('Both unit fields must be filled or neither.')
        elif e.orig.diag.constraint_name == 'accuracy_degree_must_be_specified_if_not_exact.':
            raise ValueError('Accuracy degree field must be filled if accuracy is other than exact.')

class MultipleChoiceQuestion(Question):
    __tablename__ = 'multiple_choice_questions'

    id = Column(Integer, ForeignKey('questions.id', ondelete='cascade'), primary_key=True)
    choice_one = Column(String(50), nullable=False)
    choice_two = Column(String(50), nullable=False)
    choice_three = Column(String(50), nullable=False)
    choice_four = Column(String(50), nullable=False)
    correct_answer = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint(
            """
                choice_one NOT IN (choice_two, choice_three, choice_four) AND
                choice_two NOT IN (choice_one, choice_three, choice_four) AND
                choice_three NOT IN (choice_one, choice_two, choice_four) AND
                choice_four NOT IN (choice_one, choice_two, choice_three)
            """,
            name='unique_multiple_choices',
        ),
        CheckConstraint('correct_answer >= 0 AND correct_answer <= 3', name='answer_in_range'),
    )
    __mapper_args__ = {
        'polymorphic_identity': QuestionType.mcq,
    }

    def answer_schema(self, request):
        from .forms import MultipleChoiceAnswer

        answer_choices = MultipleChoiceAnswer.prepare_choices(self)
        schema = MultipleChoiceAnswer().bind(request=request, choices=answer_choices, question=self)
        return schema

    def report(self, answer):
        choices = [self.choice_one, self.choice_two, self.choice_three, self.choice_four]
        return Question.report(self.description, choices[self.correct_answer], choices[answer])

    def handle_db_exception(e):
        if e.orig.diag.constraint_name == 'unique_multiple_choices':
            raise ValueError('All answer choices must be unique.')
        elif e.orig.diag.constraint_name == 'answer_in_range':
            raise ValueError('')

class TrueFalseQuestion(Question):
    __tablename__ = 'true_false_questions'

    id = Column(Integer, ForeignKey('questions.id', ondelete='cascade'), primary_key=True)
    correct_answer = Column(Boolean, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': QuestionType.tf,
    }

    def answer_schema(self, request):
        from .forms import TrueFalseAnswer

        return TrueFalseAnswer().bind(request=request, question=self)

    def report(self, answer):
        return Question.report(self.description, bool(self.correct_answer), bool(answer))

    #True False Questions are simple enough that they shouldn't raise any specific exceptions
    #that the create method in the super class (Question) can't handle.
    def handle_db_exception(e):
        raise ValueError('Unknown Error.')

Question.LOAD_COMPLETE_POLYMORPHIC_RELATION = with_polymorphic(Question, [MultipleChoiceQuestion, TrueFalseQuestion, MathQuestion])

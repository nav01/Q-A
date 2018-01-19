import enum

from passlib.hash import pbkdf2_sha256
from psycopg2 import errorcodes
from sqlalchemy import (
    Column, Integer, String, Boolean, Enum, ForeignKey,
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
        question_plus_type = with_polymorphic(Question, [MultipleChoiceQuestion, TrueFalseQuestion])
        questions = db.query(question_plus_type).\
            join(QuestionSet).\
            filter(Question.question_set_id == self.id).\
            order_by(question_plus_type.question_order).all()
        return questions

    def last_question_order(question_set_id, db):
        return db.query(func.coalesce(func.max(Question.question_order), -1)).filter(Question.question_set_id == question_set_id).scalar()

class QuestionType(enum.Enum):
    question = 1
    mcq = 2 #multiple choice question
    tf = 3 #true/false

    @classmethod
    def get_question_class(cls, question_type):
        if question_type == cls.mcq.name:
            return MultipleChoiceQuestion
        elif question_type == cls.tf.name:
            return TrueFalseQuestion
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
        <h4>{}</h4>
        <p>{}</p>
        <p>{}</p>
        <i class="glyphicon glyphicon {}"></i>
    '''

    @classmethod
    def report(cls, description, correct_answer, chosen_answer):
        t = cls.REPORT_TEMPLATE.format(
            description,
            correct_answer,
            chosen_answer,
            {},
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
        except Exception as _:
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

    def user_is_contributor(user_id, question_set_id, question_id, db):
        try:
            question_plus_type = with_polymorphic(Question, [MultipleChoiceQuestion, TrueFalseQuestion])
            question = db.query(question_plus_type).\
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

class MultipleChoiceQuestion(Question):
    __tablename__ = 'multiple_choice_questions'

    id = Column(Integer, ForeignKey('questions.id', ondelete='cascade'), primary_key=True)
    choice_one = Column(String(50), nullable=False)
    choice_two = Column(String(50), nullable=False)
    choice_three = Column(String(50), nullable=False)
    choice_four = Column(String(50), nullable=False)
    correct_answer = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("""
            choice_one NOT IN (choice_two, choice_three, choice_four) AND
            choice_two NOT IN (choice_one, choice_three, choice_four) AND
            choice_three NOT IN (choice_one, choice_two, choice_four) AND
            choice_four NOT IN (choice_one, choice_two, choice_three)
        """, name='unique_multiple_choices'),
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

    def edit_schema(self):
        from .forms import CSRFSchema, MultipleChoiceQuestion, merge_schemas

        csrf_schema = CSRFSchema()
        mcq_schema =  MultipleChoiceQuestion()
        merge_schemas(csrf_schema, mcq_schema)
        return csrf_schema

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

    def edit_schema(self):
        from .forms import CSRFSchema, TrueFalseQuestion, merge_schemas

        csrf_schema = CSRFSchema()
        tf_schema = TrueFalseQuestion()
        merge_schemas(csrf_schema, tf_schema)
        return csrf_schema

    def report(self, answer):
        return Question.report(self.description, bool(self.correct_answer), bool(answer))

    #True False Questions are simple enough that they shouldn't raise any specific exceptions
    #that the create method in the super class (Question) can't handle.
    def handle_db_exception(e):
        raise ValueError('Unknown Error.')

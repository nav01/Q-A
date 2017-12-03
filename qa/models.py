import itertools

from passlib.hash import pbkdf2_sha256
from psycopg2 import errorcodes
from sqlalchemy import (
    Column, Integer, String, ForeignKey,
    event,
    CheckConstraint, UniqueConstraint,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, load_only
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.schema import DDL

#There are imports at the method level of classes that have corresponding forms.
#This is to resolve an issue with cyclic imports between the forms and models modules.
#The reason for cyclic imports is so that the form fields can use database column names
#to reduce additional processing when going from form to model instance.

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
        UniqueConstraint('title','user_id'),
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
        from .forms import CSRFSchema, Topic

        csrf_schema = CSRFSchema()
        topic_schema = Topic()
        csrf_schema.children = csrf_schema.children + topic_schema.children
        return csrf_schema

class QuestionSet(Base):
    __tablename__='question_sets'

    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    topic_id = Column(Integer, ForeignKey('topics.id', ondelete='cascade'), nullable=False)

    topic = relationship('Topic', back_populates='question_sets')
    multiple_choice_questions = relationship('MultipleChoiceQuestion', back_populates='question_set', passive_deletes='all')

    __table_args__ = (
        UniqueConstraint('topic_id', 'description'),
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
        from .forms import CSRFSchema, QuestionSet

        csrf_schema = CSRFSchema()
        question_set_schema = QuestionSet()
        csrf_schema.children = csrf_schema.children + question_set_schema.children
        return csrf_schema

    #Either use each ORM class, or do this using the relationship aspect of sqlalchemy.
    #Currently not sure how to do it the 2nd way without loading unnecessary data.
    #Retrieves a list of questions.
    def get_questions(question_set_id, db):
        questions = []
        #Multiple Choice Question
        query_filter = MultipleChoiceQuestion.question_set_id == question_set_id
        result = db.query(MultipleChoiceQuestion).filter(query_filter).all()
        if result:
            questions.append(result)
        return list(itertools.chain.from_iterable(questions))

    #Returns the total number of questions associated with a question set
    def num_questions(question_set_id, db):
        question_set = db.query(QuestionSet).filter(QuestionSet.id == question_set_id).first()
        return len(question_set.multiple_choice_questions)

class Question:
    question_order = Column(Integer)
    description = Column(String,nullable=False)

    question_type = None

    #Derived classes should override and implement the following methods.
    def form_schema(self, **kwargs):
        pass

    def edit_schema(self, **kwargs):
        pass

    def report(self):
        pass

    def user_is_contributor(user_id, question_set_id, question_type, question_id, db):
        if question_type == 'mcq':
            return MultipleChoiceQuestion.user_is_contributor(user_id, question_set_id, question_id, db)
        else:
            return False

class MultipleChoiceQuestion(Base, Question):
    __tablename__='multiple_choice_questions'

    id = Column(Integer, primary_key=True)
    choice_one = Column(String(50), nullable=False)
    choice_two = Column(String(50), nullable=False)
    choice_three = Column(String(50), nullable=False)
    choice_four = Column(String(50), nullable=False)
    correct_answer = Column(Integer, nullable=False)
    question_set_id = Column(Integer, ForeignKey('question_sets.id', ondelete='cascade'), nullable=False)

    question_set = relationship('QuestionSet', back_populates='multiple_choice_questions')

    __table_args__ = (
        UniqueConstraint('question_set_id', 'description'),
        CheckConstraint(correct_answer >= 0),
        CheckConstraint(correct_answer <= 3),
    )

    question_type = 'mcq'

    def user_is_contributor(user_id, question_set_id, question_id, db):
        try:
            mcq = db.query(MultipleChoiceQuestion).\
                join(QuestionSet).\
                join(Topic).\
                join(User).\
                filter(MultipleChoiceQuestion.id == question_id, QuestionSet.id == question_set_id, User.id == user_id).one()
            return mcq
        except NoResultFound as _:
            return False

    def create(question_set_id, values, db):
        try:
            order = QuestionSet.num_questions(question_set_id,db) + 1
            new_multiple_choice_questions = [MultipleChoiceQuestion(question_set_id=question_set_id, question_order = order + i, **value)
                for i,value in enumerate(values[MultipleChoiceQuestion.__table__.name])]
            db.add_all(new_multiple_choice_questions)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            if e.orig.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise ValueError('Some submitted question(s) exist already.')
            elif e.orig.pgcode == errorcodes.CHECK_VIOLATION:
                raise ValueError('Chosen answer does not exist.')

    def edit(self, new_values, db):
        try:
            #Said to be a slow method to update via dictionary, but can't find anything better right now.
            for key, value in new_values.items():
                setattr(self, key, value)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            if e.orig.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise ValueError('A question with that description exists already.')
            elif e.orig.pgcode == errorcodes.CHECK_VIOLATION:
                raise ValueError('Chosen answer does not exist.')

    def form_schema(self, request):
        from .forms import MultipleChoiceAnswer

        answer_choices = MultipleChoiceAnswer.prepare_choices(self)
        schema = MultipleChoiceAnswer().bind(request=request,choices=answer_choices,question=self)
        return schema

    def edit_schema(self):
        from .forms import CSRFSchema, MultipleChoiceQuestion

        csrf_schema = CSRFSchema()
        mcq_schema =  MultipleChoiceQuestion()
        csrf_schema.children = csrf_schema.children + mcq_schema.children
        return csrf_schema

    def report(self, answer):
        choices = [self.choice_one, self.choice_two, self.choice_three, self.choice_four]
        chosen_answer = choices[answer]
        correct_answer = choices[self.correct_answer]
        return (self.description, correct_answer, chosen_answer, chosen_answer == correct_answer)

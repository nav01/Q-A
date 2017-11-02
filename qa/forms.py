from . import models

import colander
import deform
import re


class CSRFSchema(colander.MappingSchema):
    @colander.deferred
    def __deferred_csrf_default(node, kw):
        request = kw.get('request')
        csrf_token = request.session.get_csrf_token()
        return csrf_token

    @colander.deferred
    def __deferred_csrf_validator(node, kw):
        def validate_csrf(node, value):
            request = kw.get('request')
            csrf_token = request.session.get_csrf_token()
            if value != csrf_token:
                raise ValueError('Bad CSRF token')
        return validate_csrf

    csrf_token = colander.SchemaNode(
        colander.String(),
        default=__deferred_csrf_default,
        validator=__deferred_csrf_validator,
        widget=deform.widget.HiddenWidget(),
    )

class Topic(colander.Schema):
    __MAX_TOPIC_LENGTH = 50
    title = colander.SchemaNode(
        colander.String(),
        name=models.Topic.title.name,
        widget=deform.widget.TextInputWidget(),
        validator=colander.Length(max=__MAX_TOPIC_LENGTH),
    )
class Topics(colander.SequenceSchema):
    topic = Topic()
class TopicsSchema(CSRFSchema):
    topics = Topics(
        name=models.Topic.__table__.name,
        widget=deform.widget.SequenceWidget(orderable=True)
    )

class QuestionSet(colander.Schema):
    __MAX_DESCRIPTION_LENGTH = 100
    question_set_description = colander.SchemaNode(
        colander.String(),
        name=models.QuestionSet.description.name,
        widget=deform.widget.TextInputWidget(),
        validator=colander.Length(max=__MAX_DESCRIPTION_LENGTH),
    )
class QuestionSets(colander.SequenceSchema):
    question_set = QuestionSet()
class QuestionSetsSchema(CSRFSchema):
    #Prepares a list of topics to be used in a deform select widget.
    #Result is meant to be passed into the schema bind method so
    #it can be used in populating the widget, and also for
    #validation purposes without recreating the list.
    def prepare_topics(topics):
        choices = [('', '- Select -')]
        for topic in topics:
            choices.append((topic.id,topic.title))
        return choices

    @colander.deferred
    def set_select_choices(node, kw):
        return deform.widget.SelectWidget(values=kw.get('choices'))

    @colander.deferred
    def set_select_validator(node,kw):
        return colander.OneOf([x[0] for x in kw.get('choices')])

    topics = colander.SchemaNode(
        colander.Int(),
        name=models.QuestionSet.topic_id.name,
        widget=set_select_choices,
        validator=set_select_validator,
    )
    question_sets = QuestionSets(
        name=models.QuestionSet.__table__.name,
        widget=deform.widget.SequenceWidget(orderable=True)
    )

class MultipleChoiceQuestion(colander.Schema):
    __MAX_ANSWER_lENGTH = 50

    choices = ((0,'A'),(1,'B'),(2,'C'),(3,'D'))
    description = colander.SchemaNode(
        colander.String(),
        name=models.MultipleChoiceQuestion.description.name,
        widget=deform.widget.RichTextWidget(delayed_load=True),
        description='Enter the question description',
    )
    answer_one = colander.SchemaNode(
        colander.String(),
        name=models.MultipleChoiceQuestion.choice_one.name,
        widget=deform.widget.TextInputWidget(),
        validator=colander.Length(max=__MAX_ANSWER_lENGTH),
    )
    answer_two = colander.SchemaNode(
        colander.String(),
        name=models.MultipleChoiceQuestion.choice_two.name,
        widget=deform.widget.TextInputWidget(),
        validator=colander.Length(max=__MAX_ANSWER_lENGTH),
    )
    answer_three = colander.SchemaNode(
        colander.String(),
        name=models.MultipleChoiceQuestion.choice_three.name,
        widget=deform.widget.TextInputWidget(),
        validator=colander.Length(max=__MAX_ANSWER_lENGTH),
    )
    answer_four = colander.SchemaNode(
        colander.String(),
        name=models.MultipleChoiceQuestion.choice_four.name,
        widget=deform.widget.TextInputWidget(),
        validator=colander.Length(max=__MAX_ANSWER_lENGTH),
    )
    correct_answer = colander.SchemaNode(
        colander.Int(),
        name=models.MultipleChoiceQuestion.correct_answer.name,
        validator=colander.OneOf([x[0] for x in choices]),
        widget=deform.widget.RadioChoiceWidget(values=choices, inline=True),
        title="Choose the correct answer",
    )
class MultipleChoiceQuestions(colander.SequenceSchema):
    question = MultipleChoiceQuestion()
class MultipleChoiceSchema(CSRFSchema):
    questions = MultipleChoiceQuestions(
        name=models.MultipleChoiceQuestion.__table__.name,
        widget=deform.widget.SequenceWidget(orderable=True)
    )
class MultipleChoiceAnswer(CSRFSchema):
    def prepare_choices(question):
        choices = []
        choices.append((0, question.choice_one))
        choices.append((1, question.choice_two))
        choices.append((2, question.choice_three))
        choices.append((3, question.choice_four))
        return choices

    @colander.deferred
    def set_choices(node,kw):
        return deform.widget.RadioChoiceWidget(values=kw.get('choices'))

    @colander.deferred
    def set_validator(node,kw):
        #Could be hardcoded to a list [1..4], but the model might be changed
        #to support a variable number of choices.
        return colander.OneOf([x[0] for x in kw.get('choices')])

    @colander.deferred
    def set_title(node,kw):
        return kw.get('question').description

    question = colander.SchemaNode(
        colander.Int(),
        name='answer',
        widget=set_choices,
        validator=set_validator,
        title=set_title,
    )

class RegistrationSchema(CSRFSchema):
    def __meets_username_requirements(node,value):
        if not RegistrationSchema.USERNAME_REGEX.fullmatch(value):
            raise colander.Invalid(node, RegistrationSchema.USERNAME_REQUIREMENTS_ERROR)

    def __meets_password_requirements(node, value):
        if not RegistrationSchema.PASSWORD_REGEX.fullmatch(value):
            raise colander.Invalid(node, RegistrationSchema.PASSWORD_REQUIREMENTS_ERROR)

    #Username between 4 and 25 characters, password at least 8 characters
    USERNAME_REGEX = re.compile('^[A-Za-z]([A-Za-z_\d]){4,25}')
    PASSWORD_REGEX = re.compile('^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[$@$!%*?&_\\.])[A-Za-z\d$@$!%*?&_\\.]{8,}')
    USERNAME_REQUIREMENTS_ERROR = 'Username does not meet requirements.'
    PASSWORD_REQUIREMENTS_ERROR = 'Password does not meet requirements.'

    username = colander.SchemaNode(
        colander.String(),
        name = models.User.username.name,
        validator = __meets_username_requirements,
    )
    password = colander.SchemaNode(
        colander.String(),
        name = models.User.password.name,
        widget = deform.widget.CheckedPasswordWidget(),
        validator = __meets_password_requirements,
    )
class LoginSchema(CSRFSchema):
    username = colander.SchemaNode(
        colander.String(),
        name = models.User.username.name,
    )
    password = colander.SchemaNode(
        colander.String(),
        name = models.User.password.name,
        widget = deform.widget.PasswordWidget(),
    )

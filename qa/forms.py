import itertools

from . import models

import colander
import deform
import re

#An exception used in models.py when exceptions that should have been prevented by
#the corresponding form are raised.  This is unlikely to ever be thrown unless
#an invalid key makes it past validation which makes the dictionary expansion
#argument raise a type error, which occurs only in the 'create' methods.
class FormError(ValueError):
    def __init__(self):
        super(FormError, self).__init__('An unexpected value was submitted.')

def get_question_creation_schema(post):
    try:
        question_type = post[models.Question.type.name]
    except KeyError as e:
        raise ValueError('Question Type Not Found')
    if question_type == models.QuestionType.mcq.name:
        schema = MultipleChoiceSchema()
    elif question_type == models.QuestionType.tf.name:
        schema =  TrueFalseSchema()
    else:
        raise ValueError('Question Type Could Not Be Determined')
    return (schema, question_type)

def get_question_select_options():
    link = '/question_creation_form'
    return [
        (link, models.QuestionType.mcq.name, 'Multiple Choice'),
        (link, models.QuestionType.tf.name, 'True False'),
    ]

#Deform doesn't seem to play nicely with dynamically building schemas.
#Potentially slow method?
def merge_schemas(parent, *children):
    parent.children = parent.children + list(itertools.chain(*[child.children for child in children]))

#deform csrf protection
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

#Both wtforms and deform don't seem to easily support dynamic forms with all hidden inputs which
#would be used to reorder things like questions, so I just decided to create my own.
class ReorderResourceForm:
    input_template = '<input type="hidden" class="reorderable" id="{}" name="{}" value={}>'
    id_template = 'reorderable_{}'
    name_template = 'reorderable[{}]'
    csrf_token = 'csrf_token'

    def __init__(self, request, ids, button_name='Submit'):
        if not ids:
            raise ValueError('Empty id list.')
        self.csrf_token = request.session.get_csrf_token()
        self.ids = ids
        self.button = button_name

    def render_fields(self):
        x = self.__class__
        input_fields = [x.input_template.format(x.id_template.format(index), x.name_template.format(index), resource_id) for index, resource_id in enumerate(self.ids)]
        input_fields.append('<input type="hidden" name="{}" value="{}">'.format(self.__class__.csrf_token, self.csrf_token))
        return ''.join(input_fields)

    def validate(self, post):
        if post.get(self.__class__.csrf_token) != self.csrf_token:
            raise ValueError()
        submitted_ids = []
        try:
            index = 0
            while True:
                submitted_ids.append(int(post[self.__class__.name_template.format(index)]))
                index += 1
        except KeyError as _:
            pass
        except ValueError as _:
            raise ValueError()
        if set(submitted_ids) != set(self.ids):
            raise ValueError()
        return submitted_ids

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
        return deform.widget.SelectWidget(css_class='topic-choices', values=kw.get('choices'))

    @colander.deferred
    def set_select_validator(node,kw):
        return colander.Function(lambda value: value in [x[0] for x in kw.get('choices')], msg='Chosen topic does not exist')

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
        title='Choose the correct answer',
    )
class MultipleChoiceQuestions(colander.SequenceSchema):
    multiple_choice_question = MultipleChoiceQuestion()
class MultipleChoiceSchema(CSRFSchema):
    multiple_choice_questions = MultipleChoiceQuestions(
        name = models.MultipleChoiceQuestion.__table__.name,
        widget=deform.widget.SequenceWidget(orderable=True)
    )
    question_type = colander.SchemaNode(
        colander.String(),
        name = models.Question.type.name,
        default = models.QuestionType.mcq.name,
        validator = colander.OneOf([models.QuestionType.mcq.name]),
        widget = deform.widget.HiddenWidget(),
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
        name = 'answer',
        widget = set_choices,
        validator = set_validator,
        title = set_title,
    )

class TrueFalseQuestion(colander.Schema):
    true_choices = ('true', 1, "1")
    false_choices=('false', 0, "0")
    choices = ((1, 'True'), (0, 'False'))
    description = colander.SchemaNode(
        colander.String(),
        name = models.TrueFalseQuestion.description.name,
        widget = deform.widget.RichTextWidget(delayed_load=True),
        description = 'Enter the question description',
    )
    correct_answer = colander.SchemaNode(
        colander.Boolean(true_choices=true_choices, false_choices=false_choices, false_val=0, true_val=1),
        name = models.TrueFalseQuestion.correct_answer.name,
        validator = colander.OneOf([x[0] for x in choices]),
        widget = deform.widget.RadioChoiceWidget(values=choices, inline=True),
        title = 'Choose the correct answer',
    )
class TrueFalseQuestions(colander.SequenceSchema):
    true_false_question = TrueFalseQuestion()
class TrueFalseSchema(CSRFSchema):
    true_false_questions = TrueFalseQuestions(
        name = models.TrueFalseQuestion.__table__.name,
        widget = deform.widget.SequenceWidget(orderable=True),
    )
    question_type = colander.SchemaNode(
        colander.String(),
        name = models.Question.type.name,
        default = models.QuestionType.tf.name,
        validator = colander.OneOf([models.QuestionType.tf.name]),
        widget = deform.widget.HiddenWidget(),
    )
class TrueFalseAnswer(CSRFSchema):
    @colander.deferred
    def set_title(node,kw):
        return kw.get('question').description

    question = colander.SchemaNode(
        colander.Boolean(true_choices=TrueFalseQuestion.true_choices, false_choices=TrueFalseQuestion.false_choices, false_val=0, true_val=1),
        name = 'answer',
        validator = colander.OneOf([x[0] for x in TrueFalseQuestion.choices]),
        widget = deform.widget.RadioChoiceWidget(values=TrueFalseQuestion.choices, inline=True),
        title = set_title,
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
        description= """
            Username must be between 4 and 25 characters and cannot start with
            a number
        """,
    )
    password = colander.SchemaNode(
        colander.String(),
        name = models.User.password.name,
        widget = deform.widget.CheckedPasswordWidget(),
        validator = __meets_password_requirements,
        description = """
            Password must be between 8 and 50 characters and contain  at least
            the following:
            one uppercase letter, one lowercase letter, a number, and a special
            character.
        """
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

from pyramid.view import(
    view_config,
    view_defaults
)
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response

import colander
from deform.form import Form
from deform.exception import ValidationFailure
from . import forms
from .models import(
    MultipleChoiceQuestion as MCQ,
    QuestionSet,
    Topic,
    User,
)
from .security import(
    Session,
    requires_logged_in,
    requires_not_logged_in,
    requires_question_set_contributor,
    requires_question_contributor,
)

class QuestionSetState:
    def __init__(self, questions, question_set_id):
        if questions:
            questions.sort(key=lambda question: question.question_order)
            self.question_set_id = question_set_id
            self.question_list = questions
            self.answers = []
            self.current_question = 0
        else:
            raise ValueError('There are no questions in that set.')

    def get_current_question(self):
        return self.question_list[self.current_question]

    def get_next_question(self):
        if self.current_question == len(self.question_list) - 1:
            self.current_question += 1
            return None
        elif self.current_question == len(self.question_list):
            return None
        else:
            self.current_question += 1
            return self.question_list[self.current_question]

    def record_answer(self, answer):
        self.answers.append(answer)

    def ready_for_report(self):
        return self.current_question == len(self.question_list)

    #Returns a list of tuples (description, correct answer, chosen answer, True/False)
    def get_report(self):
        report = []
        for i, question in enumerate(self.question_list):
            report.append(question.report(self.answers[i]))
        return report

class QuestionSetViews:
    def __init__(self,request):
        self.request = request

    @view_config(route_name='view_question_set', renderer='templates/question_set.pt', decorator=(requires_logged_in, requires_question_set_contributor))
    def view_set(self):
        questions = QuestionSet.get_questions(self.request.question_set.id, self.request.db2)
        return {
            'page_title': "Viewing Question Set",
            'question_set_description': self.request.question_set.description,
            'question_set_id': self.request.question_set.id,
            'questions': questions,
        }

class QuestionViews:
    def __init__(self,request):
        self.request = request

    @view_config(route_name='create_question',renderer='templates/question_creation.pt', decorator=(requires_logged_in, requires_question_set_contributor))
    def create_question(self):
        template_vars = {'page_title':'Create Question'}
        schema = forms.MultipleChoiceSchema().bind(request=self.request)
        mcq_form = Form(schema, buttons=('create multiple choice question',))
        if self.request.method == 'POST':
            if 'create_multiple_choice_question' in self.request.POST:
                try:
                    appstruct = mcq_form.validate(self.request.POST.items())
                    question_set_id = self.request.matchdict['question_set_id']
                    MCQ.create(question_set_id,appstruct,self.request.db2)
                    return HTTPFound(self.request.route_url('profile'))
                except ValueError as e:
                    exc = colander.Invalid(mcq_form.widget, str(e))
                    mcq_form.widget.handle_error(mcq_form,exc)
                    template_vars['multiple_choice_form'] = mcq_form.render()
                except ValidationFailure as e:
                    template_vars['multiple_choice_form'] = e.render()
            else:
                template_vars['multiple_choice_form'] = mcq_form.render()
        else:
            template_vars['multiple_choice_form'] = mcq_form.render()
        return template_vars

    @view_config(route_name='delete_question', decorator=(requires_logged_in, requires_question_contributor))
    def delete_question(self):
        self.request.db2.delete(self.request.question)
        self.request.db2.commit()
        return HTTPFound(self.request.referrer)

    #Sets up the list of questions for the user to answer and presents the first question.
    #There is no progress saved and if the page is refreshed the user has to start again.
    @view_config(route_name='answer_set', renderer='templates/answer.pt', request_method='GET',decorator=(requires_logged_in, requires_question_set_contributor))
    def setup(self):
        question_set_id = self.request.matchdict['question_set_id']
        question_set = QuestionSet.get_questions(question_set_id, self.request.db2)
        try:
            template_vars = {'page_title':'Answer'} #Need better title.
            self.request.session[Session.QUESTION_STATE] = QuestionSetState(question_set,question_set_id)
            question = self.request.session[Session.QUESTION_STATE].get_current_question()
            schema = question.form_schema(self.request)
            question_form = Form(schema, buttons=('submit',))
            template_vars['question_form'] = question_form.render()
            return template_vars
        except ValueError as e:
            self.request.session.flash(str(e))
            return HTTPFound(self.request.route_url('profile'))

    @view_config(route_name='answer_set', renderer='templates/answer.pt', request_method='POST',decorator=(requires_logged_in, requires_question_set_contributor))
    def answer(self):
        if 'submit' in self.request.POST and Session.QUESTION_STATE in self.request.session:
            template_vars = {'page_title':'Answer'}
            try:
                #Store the previous question's answer.
                question = self.request.session[Session.QUESTION_STATE].get_current_question()
                schema = question.form_schema(self.request)
                question_form = Form(schema)
                appstruct = question_form.validate(self.request.POST.items())
                self.request.session[Session.QUESTION_STATE].record_answer(appstruct['answer'])

                #Present the next question.
                question = self.request.session[Session.QUESTION_STATE].get_next_question()
                if question:
                    schema = question.form_schema(self.request)
                    question_form = Form(schema, buttons=('submit',))
                    template_vars['question_form'] = question_form.render()
                else:
                    return HTTPFound(self.request.route_url('report'))
            except ValidationFailure as e:
                template_vars['question_form'] = e.render()
            return template_vars
        else:
            return HTTPFound(self.request.route_url('profile'))

    #Displays the results of the user answering the question set and clears the question
    #state in the session.
    @view_config(route_name='report', renderer='templates/report.pt',decorator=(requires_logged_in,))
    def report(self):
        template_vars = {'page_title':'Report'}
        if Session.QUESTION_STATE in self.request.session and self.request.session[Session.QUESTION_STATE].ready_for_report():
            template_vars['report'] = self.request.session[Session.QUESTION_STATE].get_report()
            del self.request.session[Session.QUESTION_STATE]
            return template_vars
        else:
            return HTTPFound(self.request.route_url('profile'))

class UserViews:
    def __init__(self,request):
        self.request = request

    #Sets variables needed for both the POST and GET versions of the  'profile' route.
    #Might do some unnecessary work depending on the outcome of the view method but improves readability.
    #Returns a dictionary to be passed to the renderer, and two deform forms, the latter of which can be None
    #if the user has not made any topics.
    def profile_vars(self):
        user = User.get_user(Session.user_id(self.request.session),self.request.db2)
        template_vars = {
            'page_title':'Profile',
            'user':user,
        }
        schema = forms.TopicsSchema().bind(request=self.request)
        add_topic_form = Form(schema, buttons=('add topics',))

        #TODO: Figure out how to make buttons multiple words without uncapitalizing every word after the first.
        if user.topics:
            schema = forms.QuestionSetsSchema().bind(request=self.request,choices=forms.QuestionSetsSchema.prepare_topics(user.topics))
            add_question_set_form = Form(schema, buttons=('add question sets',))
            return template_vars, add_topic_form, add_question_set_form
        else:
            return template_vars, add_topic_form, None

    def render_profile_forms(self, topic_form, question_set_form):
        if question_set_form:
            return topic_form.render(), question_set_form.render()
        else:
            return topic_form.render(), None

    @view_config(route_name='register', renderer='templates/register.pt', decorator=(requires_not_logged_in,))
    def register(self):
        schema = forms.RegistrationSchema().bind(request=self.request)
        form = Form(schema, buttons=('submit',))
        if self.request.method == 'POST' and 'submit' in self.request.POST:
            try:
                appstruct = form.validate(self.request.POST.items())
                user = User.create(appstruct, self.request.db2)
                Session.login(self.request.session, user)
                return HTTPFound(self.request.route_url('profile'))
            except ValueError as e:
                exc = colander.Invalid(form.widget, str(e))
                form.widget.handle_error(form,exc)
                rendered_form = form.render()
            except ValidationFailure as e:
                rendered_form = e.render()
        else:
            rendered_form = form.render()
        return {'page_title':'Register','form':rendered_form}

    @view_config(route_name='login', renderer='templates/login.pt', decorator=(requires_not_logged_in,))
    def login(self):
        schema = forms.LoginSchema().bind(request=self.request)
        form = Form(schema, buttons=('Login',))

        if self.request.method == 'POST' and 'Login' in self.request.POST:
            try:
                appstruct = form.validate(self.request.POST.items())
                user= User.login(appstruct, self.request.db2)
                if user:
                    Session.login(self.request.session, user)
                    return HTTPFound(self.request.route_url('profile'))
                else:
                    exc = colander.Invalid(form.widget, 'Username or password is incorrect.')
                    form.widget.handle_error(form, exc)
                    rendered_form = form.render()
            except ValidationFailure as e:
                rendered_form = e.render()
        else:
            rendered_form = form.render()
        return {'page_title':'Login','form':rendered_form}

    @view_config(route_name='logout',decorator=(requires_logged_in,))
    def logout(self):
        Session.logout(self.request.session)
        return HTTPFound(self.request.route_url('login'))

    @view_config(route_name='profile', renderer='templates/profile.pt', request_method='POST', decorator=(requires_logged_in,))
    def profile_post(self):
        template_vars, add_topic_form, add_question_set_form = self.profile_vars()
        if 'add_topics' in self.request.POST:
            try:
                appstruct = add_topic_form.validate(self.request.POST.items())
                Topic.create(Session.user_id(self.request.session),appstruct,self.request.db2)
                return HTTPFound(self.request.route_url('profile'))
            except ValueError as e:
                exc = colander.Invalid(add_topic_form.widget, str(e))
                add_topic_form.widget.handle_error(add_topic_form,exc)
                add_topic_form, add_question_set_form = self.render_profile_forms(add_topic_form, add_question_set_form)
            except ValidationFailure as e:
                add_topic_form, add_question_set_form = self.render_profile_forms(e, add_question_set_form)
        elif 'add_question_sets' in self.request.POST:
            try:
                appstruct = add_question_set_form.validate(self.request.POST.items())
                QuestionSet.create(appstruct,self.request.db2)
                return HTTPFound(self.request.route_url('profile'))
            except ValueError as e:
                exc = colander.Invalid(add_question_set_form.widget, str(e))
                add_question_set_form.widget.handle_error(add_question_set_form,exc)
                add_topic_form, add_question_set_form = self.render_profile_forms(add_topic_form, add_question_set_form)
            except ValidationFailure as e:
                add_topic_form, add_question_set_form = self.render_profile_forms(add_topic_form, e)

        template_vars['add_topic_form'] = add_topic_form
        if add_question_set_form:
            template_vars['add_question_set_form'] = add_question_set_form

        return template_vars

    @view_config(route_name='profile', renderer='templates/profile.pt', request_method='GET', decorator=(requires_logged_in,))
    def profile_get(self):
        if not Session.logged_in(self.request.session):
            return HTTPFound(self.request.route_url('login'))

        template_vars, add_topic_form, add_question_set_form = self.profile_vars()
        template_vars['add_topic_form'] = add_topic_form.render()
        if add_question_set_form:
            template_vars['add_question_set_form'] = add_question_set_form.render()

        if self.request.session.peek_flash():
            template_vars['errors'] = self.request.session.pop_flash()

        return template_vars

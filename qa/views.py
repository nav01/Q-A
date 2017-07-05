from pyramid.view import (
    view_config,
    view_defaults
)
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response

import colander
from deform.form import Form
from deform.exception import ValidationFailure
from . import forms
from .models import User

class UserViews:
    def __init__(self,request):
        self.request = request

    @view_config(route_name='register', renderer='templates/register.pt')
    def register(self):
        schema = forms.RegistrationSchema().bind(request=self.request)
        form = Form(schema, buttons=('submit',))

        if self.request.method == 'POST':
            if 'submit' in self.request.POST:
                try:
                    appstruct = form.validate(self.request.POST.items())
                    User.create(appstruct, self.request.db)
                    return Response('OK')
                except ValueError as e:
                    exc = colander.Invalid(form.widget, str(e))
                    form.widget.handle_error(form,exc)
                    rendered_form = form.render()
                except ValidationFailure as e:
                    rendered_form = e.render()
        else:
            rendered_form = form.render()
        return {'form':rendered_form}

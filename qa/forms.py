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

class RegistrationSchema(CSRFSchema):
    def __meets_username_requirements(node,value):
        if not RegistrationSchema.USERNAME_REGEX.fullmatch(value):
            raise colander.Invalid(node, RegistrationSchema.USERNAME_REQUIREMENTS_ERROR)

    def __meets_password_requirements(node, value):
        if not RegistrationSchema.PASSWORD_REGEX.fullmatch(value):
            raise colander.Invalid(node, RegistrationSchema.PASSWORD_REQUIREMENTS_ERROR)

    def __passwords_must_match(self,form, value):
        if not(value['password'] == value['password_confirmation']):
            raise colander.Invalid(form, RegistrationSchema.PASSWORD_MATCH_ERROR)

    USERNAME_REGEX = re.compile('^[A-Za-z]([A-Za-z_\d]){4,25}')
    PASSWORD_REGEX = re.compile('^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[$@$!%*?&_\\.])[A-Za-z\d$@$!%*?&_\\.]{8,}')
    USERNAME_REQUIREMENTS_ERROR = 'Username does not meet requirements.'
    PASSWORD_REQUIREMENTS_ERROR = 'Password does not meet requirements.'
    PASSWORD_MATCH_ERROR = 'Password fields must match.'

    validator = __passwords_must_match
    username = colander.SchemaNode(
        colander.String(),
        validator = __meets_username_requirements
    )
    password = colander.SchemaNode(
        colander.String(),
        widget = deform.widget.PasswordWidget(),
        validator = __meets_password_requirements
    )
    password_confirmation = colander.SchemaNode(
        colander.String(),
        widget = deform.widget.PasswordWidget(),
    )

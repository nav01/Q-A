import unittest

from pyramid import testing

class ReorderResourceFormTests(unittest.TestCase):
    def setUp(self):
        from qa.forms import ReorderResourceForm

        request = testing.DummyRequest()
        ids = list(range(0,3))
        self.form = ReorderResourceForm(request, ids)

    def test_init(self):
        from qa.forms import ReorderResourceForm
        request = testing.DummyRequest()
        ids = []
        self.assertRaises(ValueError, ReorderResourceForm, request, ids)
        ids.append(1)
        try:
            ReorderResourceForm(request, ids)
        except ValueError as _:
            self.fail('Non empty list falsely raised exception.')

    def test_validate(self):
        from qa.forms import ReorderResourceForm

        inputs = [ReorderResourceForm.name_template.format(i) for i in range(0,3)]
        post_data = {
            inputs[0]:0,
            inputs[1]:1,
            inputs[2]:2,
            ReorderResourceForm.csrf_token: self.form.csrf_token,
        }
        try:
            self.form.validate(post_data)
        except ValueError as _:
            self.fail('Expected successful validation.')

        del(post_data[ReorderResourceForm.csrf_token])
        self.assertRaises(ValueError, self.form.validate, post_data)

        post_data[ReorderResourceForm.csrf_token] = self.form.csrf_token
        del(post_data[inputs[0]])
        self.assertRaises(ValueError, self.form.validate, post_data)

        del(post_data[inputs[1]])
        del(post_data[inputs[2]])
        self.assertRaises(ValueError, self.form.validate, post_data)

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


class FormPostHandlerMixin:
    # handle post method for views with FormMixin and ListView/DetailView
    @method_decorator(login_required)
    def post(self, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

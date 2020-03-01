from django.contrib import admin
from django.contrib import messages as notifications
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, reverse
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormMixin

from . import InputNotInDesiredRangeError


class PasswordConfirmMixin:
    """
    Include a password_field with a FormMixin to confirm user's password before processing form data. This could also be
    written as a forms.Form mixin, but there may be cases where you don't want to use django's forms, you can use this
    mixin in those cases as well.
    """

    password_field_name = "password_confirm"  # nosec
    password_error_message = "parolanızı yanlış girdiniz"  # nosec

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            if not request.user.check_password(form.cleaned_data.get(self.password_field_name)):
                notifications.error(request, self.password_error_message)
                return self.form_invalid(form)
            return self.form_valid(form)

        return self.form_invalid(form)


class IntegratedFormMixin(FormMixin):
    """
    This mixin integrates forms with django's 'DetailView' and 'ListView'.
    """

    @method_decorator(login_required)
    def post(self, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)


class IntermediateActionMixin:
    model = None
    max_input = 500
    page_title = "Intermediate Action"
    template_name = "provide_template_name.html"

    def get(self, request):
        if not self.model:
            raise ValueError(f"Provide a model for {self.__class__.__name__}")

        try:
            context = self.get_context_data()
        except self.model.DoesNotExist:
            notifications.error(request, f"Uygun kaynak {self.model._meta.verbose_name_plural} bulunamadı.")
            return redirect(self.get_changelist_url())
        except InputNotInDesiredRangeError:
            notifications.error(request, f"Bir anda en fazla {self.max_input} {self.model._meta.verbose_name} "
                                         f"üzerinde işlem yapabilirsiniz.")
            return redirect(self.get_changelist_url())

        return render(request, self.template_name, context)

    def get_object_list(self):
        """
        Not static. If you alter the objects in a way that the current get_queryset method won't fetch them anymore,
        cast this method into a list to access the objects that are updated, after updating them.
        """
        if not self.get_queryset().exists():
            raise self.model.DoesNotExist
        return self.get_queryset()

    def get_queryset(self):
        # Filter selected objects
        queryset = self.model.objects.filter(pk__in=self.get_source_ids())
        return queryset

    def get_source_ids(self):
        source_list = self.request.GET.get("source_list", "")

        try:
            source_ids = [int(pk) for pk in source_list.split("-")]
        except (ValueError, OverflowError):
            source_ids = []

        if not source_ids:
            raise self.model.DoesNotExist

        if len(source_ids) > self.max_input:
            raise InputNotInDesiredRangeError

        return source_ids

    def get_context_data(self):
        admin_context = admin.site.each_context(self.request)
        meta = {"title": self.page_title}
        source = {"sources": self.get_object_list()}
        context = {**admin_context, **meta, **source}
        return context

    def get_changelist_url(self):
        return reverse(f"admin:{self.model._meta.app_label}_{self.model.__name__.lower()}_changelist")

from django.contrib import admin
from django.contrib import messages as notifications
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext, gettext_lazy as _
from django.views.generic import DetailView, ListView
from django.views.generic.edit import FormMixin

from dictionary.utils import InputNotInDesiredRangeError


class PasswordConfirmMixin:
    """
    Include a password_field with a FormMixin to confirm user's password before
    processing form data.
    """

    password_field_name = "password_confirm"  # nosec
    password_error_message = _("your password was incorrect")  # nosec

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

    def form_invalid(self, form):
        # Normally form views don't have get_queryset method,
        # so when you call super().form_invalid(form) it doesn't work because ListView's
        # get_context_data() interferes, and says: "Hey, if this view wants the context
        # now, then it must have defined self.object_list so I can use that to paginate it!"
        # But there is no such attribute because the view first proceeded to resolve the form.
        # So we add that attribute here in order that the view can actually process the objects.
        # We could also redirect the user, but it doesn't preserve form data.

        if isinstance(self, ListView):
            self.object_list = self.get_queryset()
        elif isinstance(self, DetailView):
            self.object = self.get_object()
        else:
            raise TypeError(
                "IntegratedFormMixin only works when the view is subclass of either DetailView or ListView."
            )

        return super().form_invalid(form)


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
            notifications.error(
                request,
                gettext("Couldn't find any suitable %(obj_name)s objects.")
                % {"obj_name": self.model._meta.verbose_name},
            )
            return redirect(self.get_changelist_url())
        except InputNotInDesiredRangeError:
            notifications.error(
                request,
                gettext("At most, you can only work with %(max_input)d %(obj_name)s objects.",)
                % {"obj_name": self.model._meta.verbose_name, "max_input": self.max_input},
            )
            return redirect(self.get_changelist_url())

        return render(request, self.template_name, context)

    def get_object_list(self):
        """
        Not static. If you alter the objects in a way that the current
        get_queryset method won't fetch them anymore, cast this method into a
        list to access the objects that are updated, after updating them.
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

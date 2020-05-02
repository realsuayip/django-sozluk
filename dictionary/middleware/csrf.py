from django.middleware.csrf import CsrfViewMiddleware as _CsrfViewMiddleware
from django.middleware.csrf import get_token


# Normally django.middleware.csrf.CsrfViewMiddleware
# ensures 'csrftoken' cookie when there is a form in a
# view (e.g. {% csrf_token %} tag is used and similar cases).

# This middleware however, ensures that ALL views regardless
# of their content set the csrf cookie. This is required because
# our website dynamically requests the csrftoken cookie.


class CsrfViewMiddleware(_CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        retval = super().process_view(request, callback, callback_args, callback_kwargs)
        # Force process_response to send the cookie
        get_token(request)
        return retval

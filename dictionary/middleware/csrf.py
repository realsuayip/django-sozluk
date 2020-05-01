from django.views.decorators.csrf import _EnsureCsrfCookie


# Normally django.middleware.csrf.CsrfViewMiddleware
# ensures 'csrftoken' cookie when there is a form in a
# view (e.g. {% csrf_token %} tag is used and similar cases).

# This middleware however, ensures that ALL views regardless
# of their content set the csrf cookie. This is required because
# our website dynamically requests the csrftoken cookie.

class CsrfViewMiddleware(_EnsureCsrfCookie):
    pass

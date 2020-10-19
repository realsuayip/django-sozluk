from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import path

from dictionary.conf import settings
from dictionary.views.auth import (
    ChangeEmail,
    ChangePassword,
    ConfirmEmail,
    CreateBackup,
    DownloadBackup,
    Login,
    Logout,
    ResendEmailConfirmation,
    SignUp,
    TerminateAccount,
)
from dictionary.views.reporting import VerifyReport

urlpatterns_password_reset = [
    path(
        "password/",
        PasswordResetView.as_view(
            template_name="dictionary/registration/password_reset/form.html",
            html_email_template_name="dictionary/registration/password_reset/email_template.html",
            from_email=settings.FROM_EMAIL,
        ),
        name="password_reset",
    ),
    path(
        "password/done/",
        PasswordResetDoneView.as_view(template_name="dictionary/registration/password_reset/done.html"),
        name="password_reset_done",
    ),
    path(
        "password/confirm/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(template_name="dictionary/registration/password_reset/confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        "password/complete/",
        PasswordResetCompleteView.as_view(template_name="dictionary/registration/password_reset/complete.html"),
        name="password_reset_complete",
    ),
]

urlpatterns_auth = urlpatterns_password_reset + [
    path("login/", Login.as_view(), name="login"),
    path("register/", SignUp.as_view(), name="register"),
    path("logout/", Logout.as_view(next_page="/"), name="logout"),
    path("email/confirm/<uuid:token>/", ConfirmEmail.as_view(), name="confirm-email"),
    path("email/resend/", ResendEmailConfirmation.as_view(), name="resend-email"),
    path("settings/password/", ChangePassword.as_view(), name="user_preferences_password"),
    path("settings/email/", ChangeEmail.as_view(), name="user_preferences_email"),
    path("settings/account-termination/", TerminateAccount.as_view(), name="user_preferences_terminate"),
    path("settings/backup/", CreateBackup.as_view(), name="user_preferences_backup"),
    path("settings/backup/download/", DownloadBackup.as_view(), name="user_preferences_backup_download"),
    path("contact/confirm/<uuid:key>/", VerifyReport.as_view(), name="verify-report"),
]

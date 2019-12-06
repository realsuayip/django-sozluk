from django.contrib import admin
from .models import Topic, Entry, Category, Author, Message, Conversation, TopicFollowing, Memento, UserVerification, \
    GeneralReport
from django.contrib.auth.admin import UserAdmin
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.contrib import messages as django_messages
from django.contrib.admin.models import LogEntry, CHANGE
from django.core.mail import send_mail
from django.contrib.contenttypes.models import ContentType
from .utils.settings import time_threshold_24h
from django.db.models import Q, Case, When, IntegerField

GENERIC_SUPERUSER_ID = 1  # generic user that does administrative actions on website, should not be a real user

# novice list related settings
application_accept_message = "sayın {}, tebrikler; yazarlık başvurunuz kabul edildi. giriş yaparak yazar olmanın olanaklarından faydalanabilirsin."
application_decline_message = 'sayın {}, yazarlık başvurunuz reddedildi ve tüm entryleriniz silindi. eğer 10 entry doldurursanız tekrar çaylak onay listesine alınacaksınız.'


def novice_full_list():
    novice_list = Author.objects.filter(is_novice=True, application_status="PN").annotate(
        activity=Case(When(Q(last_activity__gt=time_threshold_24h), then=1),
                      When(Q(last_activity__lte=time_threshold_24h), then=2), output_field=IntegerField(), )).order_by(
        "activity", "application_date")
    return novice_list


def log_admin(msg, authorizer, model_type, model_object, flag=CHANGE):
    LogEntry.objects.log_action(user_id=authorizer.id, content_type_id=ContentType.objects.get_for_model(model_type).pk,
                                object_id=model_object.id, object_repr=f"{msg}", action_flag=flag)


class CustomUserAdmin(UserAdmin):
    model = Author
    raw_id_fields = ['favorite_entries', 'upvoted_entries', 'downvoted_entries', 'following', 'blocked', 'pinned_entry']

    fieldsets = UserAdmin.fieldsets + ((None, {'fields': (
        'is_novice', 'application_status', 'application_date', 'last_activity', 'banned_until', 'birth_date', 'gender',
        'following', "blocked", 'favorite_entries', 'upvoted_entries', 'downvoted_entries', 'pinned_entry')}),)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('novices/', self.admin_site.admin_view(self.novice_list), name="novice_list"),
                   path('novices/<str:username>/', self.admin_site.admin_view(self.novice_lookup),
                        name="novice_lookup"), ]
        return my_urls + urls

    def novice_list(self, request):
        """
            View to list top 10 novices.
        """
        if not request.user.has_perm('dictionary.can_activate_user'):
            return HttpResponseForbidden("403 Forbidden")

        novices = novice_full_list()[:10]
        context = dict(self.admin_site.each_context(request), title="Çaylak onay listesi", objects=novices)
        return TemplateResponse(request, "dictionary/admin/novices.html", context)

    def novice_lookup(self, request, username):
        """
        View to accept or reject a novice application. Lists first 10 entries of the novice user. Users will get mail
        and a message indicating the result of their application. A LogEntry object is created for this action.
        """

        if not request.user.has_perm('dictionary.can_activate_user'):
            return HttpResponseForbidden("403 Forbidden")

        user = get_object_or_404(Author, username=username)

        if request.method == "POST":
            op = request.POST.get("operation")

            if op not in ["accept", "decline"]:
                django_messages.add_message(request, django_messages.ERROR, "Geçersiz bir işlem seçtiniz.")
                return HttpResponseRedirect(reverse("admin:novice_lookup", kwargs={"username": username}))
            else:
                if op == "accept":
                    user.application_status = "AP"
                    user.is_novice = False
                    user.save()
                    log_admin(f"{user.username} nickli kullanıcının yazarlık talebi kabul edildi", request.user, Author,
                              user)
                    Message.objects.compose(Author.objects.get(id=GENERIC_SUPERUSER_ID), user,
                                            application_accept_message.format(user.username))
                    send_mail('yazarlık başvurunuz kabul edildi', application_accept_message.format(user.username),
                              'Django Sözlük <correct@email.com>', [user.email], fail_silently=False, )
                    django_messages.add_message(request, django_messages.SUCCESS,
                                                f"'{username}' nickli kullanıcının yazarlık talebini kabul ettiniz.")
                elif op == "decline":
                    Entry.objects_published.filter(author=user).delete()  # does not trigger model's delete()
                    user.application_status = "OH"
                    user.application_date = None
                    user.save()
                    log_admin(f"{user.username} nickli kullanıcının yazarlık talebi kabul reddedildi", request.user,
                              Author, user)
                    Message.objects.compose(Author.objects.get(id=GENERIC_SUPERUSER_ID), user,
                                            application_decline_message.format(user.username))
                    send_mail('yazarlık başvurunuz reddedildi', application_decline_message.format(user.username),
                              'Django Sözlük <correct@email.com>', [user.email], fail_silently=False, )
                    django_messages.add_message(request, django_messages.SUCCESS,
                                                f"'{username}' nickli kullanıcının yazarlık talebini reddettiniz.")

                if request.POST.get("submit_type") == "redirect_back":
                    return HttpResponseRedirect(reverse("admin:novice_list"))
                else:
                    return HttpResponseRedirect(
                        reverse("admin:novice_lookup", kwargs={"username": request.POST.get("submit_type")}))

        # novices = Author.objects.filter(is_novice=True, application_status="PN")
        if user not in novice_full_list():
            django_messages.add_message(request, django_messages.ERROR, "kullanıcı çaylak onay listesinde değil.")
            return HttpResponseRedirect(reverse("admin:novice_list"))
        elif user not in novice_full_list()[:10]:
            # not tested throughly
            django_messages.add_message(request, django_messages.ERROR,
                                        "kullanıcı çaylak onay listesinin başında değil")
            return HttpResponseRedirect(reverse("admin:novice_list"))

        first_ten_entries = Entry.objects_published.filter(author=user).order_by("id")[:10]

        # Determines next user for the continue button.
        next_user = Author.objects.filter(is_novice=True, application_status="PN",
                                          last_activity__gte=time_threshold_24h,
                                          application_date__gt=user.application_date).order_by(
            "application_date").first()

        if not next_user:
            # There was no user with latest activity. Check for non-active ones.
            next_user = Author.objects.filter(is_novice=True, application_status="PN",
                                              application_date__gt=user.application_date).order_by(
                "application_date").first()

        next_username = next_user.username if next_user else None
        context = dict(self.admin_site.each_context(request), title=f"{username} isimli çaylağın ilk 10 entry'si",
                       entries=first_ten_entries, next=next_username)

        return TemplateResponse(request, "dictionary/admin/novice_lookup.html", context)


class CategoryAdmin(admin.ModelAdmin):
    exclude = ("slug",)


class GeneralReportAdmin(admin.ModelAdmin):
    list_display = ("subject", "reporter_email", "is_open",)
    readonly_fields = ('reporter_email', 'category', 'subject', 'content')

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-is_open")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.index_template = "dictionary/admin/index_custom.html"
admin.site.register(Author, CustomUserAdmin)
admin.site.register(Topic)
admin.site.register(Entry)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Message)
admin.site.register(Conversation)
admin.site.register(TopicFollowing)
admin.site.register(Memento)
admin.site.register(UserVerification)
admin.site.register(GeneralReport, GeneralReportAdmin)

# Register your models here.

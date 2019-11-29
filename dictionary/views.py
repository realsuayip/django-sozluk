import datetime
import math
import random
from decimal import Decimal

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Max, Q, Case, When, F, IntegerField, Min, Count
from django.http import Http404, HttpResponseRedirect, JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import View, ListView, UpdateView
from django.views.generic.edit import FormView
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_decode

from .forms import SignUpForm, EntryForm, SendMessageForm, LoginForm, PreferencesForm, ChangeEmailForm, ResendEmailForm
from .models import Entry, Category, Topic, Author, Message, Conversation, TopicFollowing, Memento, UserVerification
from .util import time_threshold_24h, ENTRIES_PER_PAGE, ENTRIES_PER_PAGE_PROFILE, nondb_categories, vote_rates, \
    require_ajax, find_after_page, mark_read, TOPICS_PER_PAGE, YEAR_RANGE, send_email_confirmation

from .merge_with_util import TopicListManager
from .utils.views import AjaxView
from .utils.decorators import ajax_post, ajax_get


# flatpages for about us etc.
# todo imports according to pep8
# todo scrollbar tracking
# todo converation pagenation
# todo karma skor!
# todo hayvan ara !!
# todo: get_or_create for entry cretion topic shit xd
# ALL views will be converted to class based views.
# todo convert ajax views to class based-> with mixins
# https://stackoverflow.com/questions/33256096/django-order-by-the-amount-of-comments

def index(request):
    # some prototypes
    latest_entry_time = dict(last_entry_dt=Max('entries__date_created'))
    last_24_hour_filter = dict(entries__date_created__gte=time_threshold_24h)

    prev_24_hour_topics = Topic.objects.annotate(**latest_entry_time).filter(**last_24_hour_filter).order_by(
        '-last_entry_dt')

    #print(prev_24_hour_topics)

    prev_25_hour_topics = Topic.objects.annotate(last_entry_dt=Max('entries__date_created'),
                                                 entry_count=Count("entries", filter=Q(
                                                     entries__date_created__gte=time_threshold_24h))).filter(
        entries__date_created__gte=time_threshold_24h).order_by('-last_entry_dt').values_list("title", "slug", "entry_count")

    print(prev_25_hour_topics)

    return render(request, "index.html")


@login_required
def people(request):
    blocked = request.user.blocked
    following = request.user.following
    data = {"blocked": blocked, "following": following}
    return render(request, "people.html", context=data)


@login_required
def messages(request):
    conversations = Conversation.objects.list_for_user(request.user)
    return render(request, "conversation/inbox.html", context={"conversations": conversations})


#
# class ConversationList(ListView, LoginRequiredMixin):
#     model = Conversation
#     paginate_by = 1
#     template_name = "inbox.html"
#     context_object_name = "conversations"
#
#     def get_queryset(self):
#         return Conversation.objects.list_for_user(self.request.user)
class UserPreferences(LoginRequiredMixin, UpdateView):
    model = Author
    form_class = PreferencesForm
    template_name = "user/preferences/index.html"

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        django_messages.add_message(self.request, django_messages.INFO, "kaydettik efendim")
        return reverse("user_preferences")

    def form_invalid(self, form):
        django_messages.add_message(self.request, django_messages.INFO, "bir şeyler ters gitti")
        return super().form_invalid(form)


class ActivityList(LoginRequiredMixin, ListView):
    model = TopicFollowing
    template_name = "activity.html"
    context_object_name = "topics_following"

    # todo from onread anchor link
    def get_queryset(self):
        return TopicFollowing.objects.filter(author=self.request.user).annotate(
            latest=Max("topic__entries__date_created"),
            is_read=Case(When(Q(latest__gt=F("read_at")), then=1), When(Q(latest__lt=F("read_at")), then=2),
                         output_field=IntegerField()), ).order_by("is_read", "-read_at")


class CategoryList(ListView):
    model = Category
    template_name = "category_list.html"
    context_object_name = "categories"


class EntryUpdate(LoginRequiredMixin, UpdateView):
    model = Entry
    form_class = EntryForm
    template_name = "entry_update.html"
    context_object_name = "entry"

    def dispatch(self, request, *args, **kwargs):
        if self.get_object().author != request.user:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        if self.get_object().is_draft:
            django_messages.add_message(self.request, django_messages.INFO, "yazdım bir kenara")
            return reverse("entry_update", kwargs={"pk": self.get_object().pk})
        else:
            return reverse("entry_permalink", kwargs={"entry_id": self.get_object().pk})

    def form_valid(self, form):
        entry_is_draft_initial = self.get_object().is_draft  # returns True is the object is draft
        entry = form.save(commit=False)

        if entry_is_draft_initial:
            # updating draft
            entry.date_edited = None
            if not entry.is_draft:  # entry is published by user
                entry.date_created = timezone.now()
        else:
            entry.is_draft = False
            # updating published entry
            entry.date_edited = timezone.now()
        entry.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        try:
            obj = Entry.objects_all.get(pk=pk)
        except Entry.DoesNotExist:
            raise Http404
        return obj


@login_required
def conversation(request, username):
    recipient = get_object_or_404(Author, username=username)

    # conversation with self is not allowed
    if recipient == request.user:
        raise Http404

    form = SendMessageForm()
    if request.method == "POST":
        form = SendMessageForm(request.POST)
        if form.is_valid():
            msg = Message.objects.compose(request.user, recipient, form.cleaned_data['body'])
            if not msg:
                django_messages.add_message(request, django_messages.INFO, "mesajınızı gönderemedik ne yazık ki")
            return HttpResponseRedirect(reverse('conversation', kwargs={'username': username}))

    # todo bunu ajaxlıya da ekle success olunca <3
    conversation_object = Conversation.objects.with_user(request.user, recipient)

    # mark messages read
    if conversation_object:
        for message in conversation_object.messages.filter(
                sender=recipient):  # todo check if read_at is null before changing
            message.read_at = timezone.now()
            message.save()

    data = {"conversation": conversation_object, "recipient": recipient, "form": form}
    return render(request, "conversation/conversation.html", context=data)


class ComposeMessage(AjaxView):
    login_required = True
    require_method = "POST"

    def handle(self):
        return self.compose()

    def compose(self):
        message_body = self.request_data.get("message_body")
        if len(message_body) < 3:
            self.error_message = "az bir şeyler yaz yeğenim"
            return self.error(status=200)

        try:
            recipient = Author.objects.get(username=self.request_data.get("recipient"))
        except Author.DoesNotExist:
            self.error_message = "öyle birini bulamadım valla"
            return self.error(status=200)

        msg = Message.objects.compose(self.request.user, recipient, message_body)

        if not msg:
            self.error_message = "mesajınızı gönderemedik ne yazık ki"
            return self.error(status=200)
        else:
            self.success_message = "mesajınız sağ salim gönderildi"
            return self.success()


class TopicList(ListView):
    """
        Topic list (başlıklar) for mobile views such as "bugün", "gündem",
        Desktop equivalent => TopicListAsync

        cache_key for bugun-> bugun_extended_{self.request.user.id} (also used in _category)
        refresh_count -> for bugun only, "yenile" button count
    """
    model = Topic
    context_object_name = "topics"
    template_name = "topic_list.html"
    paginate_by = TOPICS_PER_PAGE
    refresh_count = 0

    def get_queryset(self):
        year = None
        slug = self.kwargs['slug']
        if slug == "tarihte-bugun":

            if self.request.GET.get("year"):
                year = self.request.GET.get("year")
                self.request.session["year"] = year
            else:
                year = self.request.session.get("year")

            if not year:
                year = random.choice(YEAR_RANGE)
                self.request.session["year"] = year

            try:
                if int(year) not in YEAR_RANGE:
                    year = None
            except ValueError:
                year = None

        if slug == "bugun" and not self.request.user.is_authenticated:
            return self.model.objects.none()

        manager = TopicListManager(self.request.user, slug, extend=True, year=year)
        self.refresh_count = manager.refresh_count
        return manager.serialized

    def get_context_data(self, **kwargs):
        slug = self.kwargs['slug']
        nondb_safename = {"bugun": "bugün", "gundem": "gündem", "basiboslar": "başıboşlar", "takip": "takip",
                          "tarihte-bugun": "tarihte bugün", "kenar": "kenar", "caylaklar": "çaylaklar",
                          "debe": "dünün en beğenilen entry'leri", }
        if slug in nondb_categories:
            title = nondb_safename[slug]
        else:
            title = Category.objects.get(slug=slug).name
        context = super().get_context_data(**kwargs)
        context['page_safename'] = title
        if self.request.session.get("year"):
            context["current_year"] = self.request.session.get("year")
        context['slug_name'] = slug
        if slug == "tarihte-bugun":
            context["year_range"] = YEAR_RANGE

        context['refresh_count'] = self.refresh_count
        return context

    @method_decorator(login_required)
    def post(self, *args, **kwargs):
        if self.kwargs['slug'] == "bugun":
            # reset cache (refresh button mobile click event)
            manager = TopicListManager(self.request.user, "bugun", extend=True)
            manager.delete_cache()
            return redirect(self.request.path)
        return HttpResponseBadRequest()


class Login(LoginView):
    # TODO: login_required varken yanlış yönlendirme yapıo
    form_class = LoginForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me", False)
        if remember_me:
            self.request.session.set_expiry(1209600)  # 2 weeks
        else:
            self.request.session.set_expiry(7200)

        success_message = "başarıyla giriş yaptınız efendim"
        django_messages.add_message(self.request, django_messages.INFO, success_message)
        return super().form_valid(form)


class Logout(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            success_message = "başarıyla çıkış yaptınız efendim"
            django_messages.add_message(self.request, django_messages.INFO, success_message)
        return super().dispatch(request)


class ChangePassword(PasswordChangeView):
    success_url = reverse_lazy("user_preferences")
    template_name = "user/preferences/password.html"

    def form_valid(self, form):
        django_messages.add_message(self.request, django_messages.INFO, "işlem tamam")
        return super().form_valid(form)


class ChangeEmail(LoginRequiredMixin, FormView):
    template_name = "user/preferences/email.html"
    form_class = ChangeEmailForm
    success_url = reverse_lazy("user_preferences")

    def form_valid(self, form):
        if not self.request.user.check_password(form.cleaned_data.get("password_confirm")):
            django_messages.add_message(self.request, django_messages.INFO, "parolanızı yanlış girdiniz")
            return redirect(reverse("user_preferences_email"))

        send_email_confirmation(self.request.user, form.cleaned_data.get("email1"))
        django_messages.add_message(self.request, django_messages.INFO,
                                    "e-posta onayından sonra adresiniz değişecektir.")
        return redirect(self.success_url)


class ConfirmEmail(View):
    success = False

    def get(self, request, uidb64, token):
        try:
            user_id = urlsafe_base64_decode(uidb64).decode()
            verification_object = UserVerification.objects.get(author_id=user_id,
                                                               expiration_date__gte=time_threshold_24h)
        except (ValueError, UnicodeDecodeError, ObjectDoesNotExist):
            return self.response()

        if check_password(token, verification_object.verification_token):
            author = Author.objects.get(id=user_id)
            if not author.is_active:
                author.is_active = True
                author.save()
            else:
                author.email = verification_object.new_email
                author.save()

            self.success = True
            UserVerification.objects.filter(author=author).delete()

        return self.response()

    def response(self):
        return render(self.request, "registration/email_confirmation_result.html", context={"success": self.success})


class ResendEmailConfirmation(FormView):
    form_class = ResendEmailForm
    template_name = "registration/email_resend_form.html"

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        author = Author.objects.get(email=email)
        send_email_confirmation(author, email)
        django_messages.add_message(self.request, django_messages.INFO,
                                    "onaylama bağlantısını içeren e-posta gönderildi")
        return redirect("login")


class SignUp(FormView):
    """
        todo: usernamelerde türkçe karakter olmayacak. kontrol mekanizması yapçaz.
    """
    form_class = SignUpForm
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        user = form.save(commit=False)
        user.username = form.cleaned_data.get('username').lower()
        user.birth_date = form.cleaned_data.get('birth_date')
        user.gender = form.cleaned_data.get('gender')
        user.save()
        send_email_confirmation(user, user.email)
        django_messages.add_message(self.request, django_messages.INFO,
                                    "e-posta adresinize bir onay bağlantısı gönderildi."
                                    "bu bağlantıya tıklayarak hesabınızı aktif hale getirip giriş yapabilirsiniz.")
        return redirect('login')


def user_profile(request, username):
    profile = get_object_or_404(Author, username=username)
    data = {"author": profile}

    if request.user.is_authenticated:
        if request.method == "POST":
            body = request.POST.get("memento")
            obj, created = Memento.objects.update_or_create(holder=request.user, patient=profile,
                                                            defaults={"body": body})
            data["memento"] = obj.body
            django_messages.add_message(request, django_messages.INFO, "kaydettik efendim")
            return redirect(reverse("user_profile", kwargs={"username": profile.username}))
        else:
            try:
                data["memento"] = Memento.objects.get(holder=request.user, patient=profile).body
            except ObjectDoesNotExist:
                pass

        if request.user in profile.blocked.all() or profile in request.user.blocked.all():
            raise Http404

        if request.user == profile and profile.is_novice and profile.application_status == "PN":
            if request.session.get("novice_queue"):
                data['novice_queue'] = request.session["novice_queue"]
            else:
                data['novice_queue'] = False

    page_tab = request.GET.get("t")

    if page_tab == "favorites":
        data['tab'] = "favorites"
        entries = profile.favorite_entries.filter(author__is_novice=False).order_by("-date_created")
    elif page_tab == "popular":
        data['tab'] = "popular"
        entries = Entry.objects_published.filter(author=profile, vote_rate__gt=Decimal("1"))
    else:
        data['tab'] = "entries"
        entries = Entry.objects_published.filter(author=profile).order_by("-date_created")

    paginator = Paginator(entries, ENTRIES_PER_PAGE_PROFILE)
    page = request.GET.get("page")
    entries_list = paginator.get_page(page)
    data['entries'] = entries_list

    return render(request, "user/user_profile.html", context=data)


def topic(request, slug=None, entry_id=0, unicode=None):
    """ THIS VIEW WILL BE CONVERTED TO CLASS BASED"""

    # todo: başlık yönlendirme (türkçe düzeltme gibi.)
    # todo: entry baslıklarının nasıl olacağına dair bir regex yapıp titleyi kontrol et (başlık formatı)
    # todo topic__slug => topic_object
    """
        Sorry, This view is a bit complicated/non-intuitive even.
        1. Site-wide searches with q parameter. (request.GET.get("q"))
        2. List of (un)filtered entries. [by topic.slug or topic.title (unicode string) or q(uery)] filtered by 'a' (mode)
        3. Permanlinks for an entry. (entry_id)
    """
    query = request.GET.get("q")
    pseudo_topic = None

    if not slug and not unicode and not query and not entry_id:
        # empty request
        return HttpResponseRedirect(reverse("home"))

    if entry_id:
        entry = get_object_or_404(Entry, id=entry_id)
        if request.user.is_authenticated:
            if entry.author in request.user.blocked.all():
                raise Http404

        slug = entry.topic.slug

    data = {'form': EntryForm(), 'slug': slug}

    try:
        # topic_object also used for entry_permalink view (below)
        topic_object = Topic.objects.get(slug=slug)
    except ObjectDoesNotExist:
        topic_object = False

    if (not topic_object or unicode or query) and not entry_id:
        # handling of: q parameter, string.unicode (for Turkish characters) and non-existent slugs
        # title in this block refers to: 'topic_title' (and also @username and #entry_id if query exists)

        if unicode:
            title = unicode
        elif slug and not topic_object:
            title = slug
        else:
            # site-wide search for Author and Entry objects
            title = query
            if title.startswith("@") and len(title) > 1:
                return redirect("user_profile", username=title[1:])
            elif title.startswith("#"):
                if not title[1:].isdigit():
                    pass
                else:
                    return redirect("entry_permalink", entry_id=title[1:])

        # redirecting for str.unicode and q?=<topic_title>
        try:
            title_redirect = Topic.objects.get(title=title)
            return redirect("topic", slug=title_redirect.slug)
        except ObjectDoesNotExist:
            pass

        # no corresponding topic object found
        pseudo_topic = {"title": title}
        data['topic_exists'] = False
        data['topic'] = pseudo_topic

        if request.method != "POST":
            return render(request, "entry_list.html", context=data)

    # entry creation handling
    if request.method == "POST":
        if pseudo_topic:
            # user creates a brand new topic
            # todo yönelendirme draft
            topic_object = Topic.objects.create(title=pseudo_topic['title'], created_by=request.user)

        form = EntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            if form.cleaned_data.get("is_draft"):
                entry.is_draft = True
            entry.topic = topic_object
            entry.author = request.user
            entry.save()
            return HttpResponseRedirect(reverse('entry_permalink', kwargs={'entry_id': entry.id}))

    # handling of: valid slugs with parameters "day", "year (tarihte-bugun)", "todo: gundem"
    entries = None
    if (slug and request.GET.get("year") or request.GET.get("day") or request.GET.get("a")) and not entry_id:
        look_for_before = False
        look_for_after = False

        if request.GET.get("year", None):
            year = request.GET.get("year")
            try:
                if int(year) in range(1999, 2030):
                    now = datetime.datetime.now()
                    entries = Entry.objects.filter(topic__slug=slug, date_created__year=year, date_created__day=now.day,
                                                   date_created__month=now.month)
                    look_for_before = True
                    look_for_after = True
            except ValueError:
                pass

        elif request.GET.get("day") == "today":
            entries = Entry.objects.filter(topic__slug=slug, date_created__gte=time_threshold_24h)
            if Entry.objects.filter(topic__slug=slug, date_created__lt=time_threshold_24h).exists():
                look_for_before = True

        elif request.GET.get("a"):
            # handling of things such as "şükela modu, başlıkta ara and other delimiters"
            mode = request.GET.get("a")
            if mode == "nice":
                entries = Entry.objects.filter(topic__slug=slug).order_by("-vote_rate")
                data['mode'] = "nice"
            elif mode == "nicetoday":
                data['mode'] = "nicetoday"
                look_for_before = True
                entries = Entry.objects.filter(topic__slug=slug, date_created__gte=time_threshold_24h).order_by(
                    "-vote_rate")
            elif mode == "search":
                keywords = request.GET.get("keywords")
                if keywords:
                    look_for_before = True
                    look_for_after = True
                    if keywords.startswith("@"):
                        try:
                            author = Author.objects.get(username=keywords[1:])
                            entries = Entry.objects.filter(topic__slug=slug, author=author)
                        except Author.DoesNotExist:
                            entries = None
                    else:
                        # use postgre to make searches more advanced
                        entries = Entry.objects.filter(topic__slug=slug, content__icontains=keywords)
            elif mode == "following":
                if request.user.is_authenticated:
                    if not TopicFollowing.objects.filter(topic=topic_object, author=request.user).exists:
                        entries = None
                    else:
                        date = request.GET.get("d")
                        try:
                            last_read = datetime.datetime.fromtimestamp(int(date))
                        except (ValueError, TypeError, OSError):
                            last_read = None
                            entries = None

                        if last_read:
                            try:
                                entries = Entry.objects.filter(topic=topic_object, date_created__gt=last_read).exclude(
                                    Q(author__in=request.user.blocked.all()) | Q(author=request.user))
                            except Entry.DoesNotExist:
                                pass

                    if not entries:
                        django_messages.add_message(request, django_messages.INFO,
                                                    "pek bişey bulamadım açıkçası, buyrun hepsi")
                        return redirect("topic", slug=topic_object.slug)
                    else:
                        mark_read(topic_object, request.user)
                        look_for_before = True
                        django_messages.add_message(request, django_messages.INFO, f"{entries.count()} tane entry")

            elif mode == "caylaklar":
                look_for_before = True
                look_for_after = True
                # Entry.caylaklar.filter todo
                entries = Entry.objects_novices.filter(topic__slug=slug, date_created__gte=time_threshold_24h)

        if request.user.is_authenticated and entries:
            entries = entries.exclude(author__in=request.user.blocked.all())

        if entries:
            paginator = Paginator(entries, ENTRIES_PER_PAGE)
            # we should find the entry with oldest date, not idx. todo
            page = request.GET.get("page")
            entries_list = paginator.get_page(page)
            before, before_page = None, None
            if look_for_before:
                if request.GET.get("a") == "dailynice":
                    earliest = entries.earliest("date_created").date_created
                else:
                    earliest = entries_list[0].date_created
                before = Entry.objects.filter(topic__slug=slug, date_created__lt=earliest).count()
                before_page = math.ceil(before / ENTRIES_PER_PAGE)

            if before:
                data['entries_before'] = before
                data['before_page'] = before_page

            if look_for_after:
                # If some error occurs, look for numbers
                after = Entry.objects.filter(topic__slug=slug, date_created__gt=entries_list[-1].date_created).count()
                data['entries_after'] = after
                data['after_page'] = find_after_page(before)
    else:
        if not entry_id:
            # no parameters, so pass all entries
            entries = Entry.objects.filter(topic__slug=slug)

    if (not entries and request.method != "POST") and not entry_id:
        data['err'] = "başlıkta aradığınız kriterlere uygun giriş bulunamadı"
        data['topic'] = {"title": Topic.objects.get(slug=slug).title, "slug": slug, }
        data['entries_after'] = Entry.objects.filter(topic=Topic.objects.get(slug=slug)).count()
        return render(request, "entry_list.html", context=data)

    if entry_id:
        entries_list = None
        entry_perma = Entry.objects_all.get(id=entry_id)
        if entry_perma.is_draft:
            django_messages.add_message(request, django_messages.INFO, "kenara attık onu")
            return redirect(reverse("topic", kwargs={"slug": entry_perma.topic.slug}))

        data['entry_perma'] = entry_perma
        before = Entry.objects.filter(topic__slug=slug, date_created__lt=entry_perma.date_created).count()
        after = Entry.objects.filter(topic__slug=slug, date_created__gt=entry_perma.date_created).count()
        after_page = find_after_page(before)
        before_page = math.ceil(before / ENTRIES_PER_PAGE)
        data['entries_before'] = before
        data['before_page'] = before_page
        data['entries_after'] = after
        data['after_page'] = after_page
    else:
        if request.user.is_authenticated:
            entries = entries.exclude(author__in=request.user.blocked.all())

        paginator = Paginator(entries, ENTRIES_PER_PAGE)
        page = request.GET.get("page")
        entries_list = paginator.get_page(page)

    data['entries'] = entries_list
    data['topic_exists'] = True if topic_object.has_entries() else False
    data['topic'] = topic_object

    return render(request, "entry_list.html", context=data)


# ajax views
class AutoComplete(AjaxView):
    require_method = "GET"

    def handle(self):
        if self.request_data.get("author"):
            return self.author()
        elif self.request_data.get("query"):
            return self.query()

        super().handle()

    def author(self):
        objects = Author.objects.filter(username__istartswith=self.request_data.get("author"))
        response = [obj.username for obj in objects]
        return JsonResponse({"suggestions": response})

    def query(self):
        query = self.request_data.get("query")

        if query.startswith("@"):
            if len(query) <= 1:
                response = ["@"]
            else:
                response = ["@" + obj.username for obj in Author.objects.filter(username__istartswith=query[1:])[:7]]
        else:
            response = [obj.title for obj in Topic.objects.filter(title__istartswith=query)[:7]]

            for extra in Topic.objects.filter(title__icontains=query)[:7]:
                if len(response) >= 7:
                    break
                if extra.title not in response:
                    response.append(extra.title)

            extra_authors = Author.objects.filter(username__istartswith=query)[:3]
            for author in extra_authors:
                response.append("@" + author.username)
        return JsonResponse({"suggestions": response})


class AsyncTopicList(AjaxView):
    require_method = "GET"

    def handle(self):
        slug = self.kwargs.get("slug")
        year = self.request_data.get("year") if slug == "tarihte-bugun" else None

        if year:
            try:
                if not int(year) in YEAR_RANGE:
                    return self.bad_request()
            except(ValueError, OverflowError):
                return self.bad_request()

        extend = True if self.request_data.get("extended") == "yes" else False
        fetch_cached = False if self.request_data.get("nocache") == "yes" else True
        manager = TopicListManager(self.request.user, slug, year=year, extend=extend, fetch_cached=fetch_cached)
        return JsonResponse({"topic_data": manager.serialized, "refresh_count": manager.refresh_count}, safe=False)


class Vote(AjaxView):
    """
    Anonymous users can vote, in order to hinder duplicate votings, session is used; though it is not
    the best way to handle this, I think it's better than storing all the IP adresses of the guest users as acquiring an
    IP adress is a nuance; it depends on the server and it can also be manipulated by keen hackers. It's just better to
    stick to this way instead of making things complicated as there is no way to make this work 100% intended.
    """
    require_method = "POST"

    # View specific attributes
    vote = None
    entry = None
    already_voted = False
    already_voted_type = None
    anonymous = True
    anon_votes = None
    cast_up = None
    cast_down = None

    def handle(self):
        self.vote = self.request_data.get("vote")
        self.cast_up = True if self.vote == "up" else False
        self.cast_down = True if self.vote == "down" else False

        try:
            self.entry = get_object_or_404(Entry, id=int(self.request_data.get("entry_id")))
        except (ValueError, OverflowError):
            return self.error()

        if self.request.user.is_authenticated:
            # self-vote not allowed
            if self.request.user == self.entry.author:
                return self.error()
            self.anonymous = False

        if self.vote in ["up", "down"]:
            if self.cast():
                return self.success()

        super().handle()

    def cast(self):
        entry, cast_up, cast_down = self.entry, self.cast_up, self.cast_down
        reduce, increase = vote_rates["reduce"], vote_rates["increase"]

        if self.anonymous:
            k = vote_rates["anonymous_multiplier"]
            self.anon_votes = self.request.session.get("anon_votes")
            if self.anon_votes:
                for record in self.anon_votes:  # do not use the name 'record' method's this scope
                    if record.get("entry_id") == entry.id:
                        self.already_voted = True
                        self.already_voted_type = record.get("type")
                        break
        else:
            k = vote_rates["authenticated_multiplier"]
            sender = self.request.user
            if entry in sender.upvoted_entries.all():
                self.already_voted = True
                self.already_voted_type = "up"
            elif entry in sender.downvoted_entries.all():
                self.already_voted = True
                self.already_voted_type = "down"

        if self.already_voted:
            if self.already_voted_type == self.vote:
                # Removes the vote cast.
                if cast_up:
                    entry.update_vote(reduce * k)
                elif cast_down:
                    entry.update_vote(increase * k)
            else:
                # Changes the vote cast.
                if cast_up:
                    entry.update_vote(increase * k, change=True)
                if cast_down:
                    entry.update_vote(reduce * k, change=True)
        else:
            # First time voting.
            if cast_up:
                entry.update_vote(increase * k)
            elif cast_down:
                entry.update_vote(reduce * k)

        if self.record_vote():
            return True
        return False

    def record_vote(self):
        entry, cast_up, cast_down = self.entry, self.cast_up, self.cast_down
        prior_cast_up = True if self.already_voted_type == "up" else False
        prior_cast_down = True if self.already_voted_type == "down" else False

        if self.anonymous:
            anon_votes_new = []
            if self.already_voted:
                anon_votes_new = [y for y in self.anon_votes if y.get('entry_id') != entry.id]
                if self.already_voted_type != self.vote:
                    anon_votes_new.append({"entry_id": entry.id, "type": self.vote})
            else:
                if self.anon_votes:
                    self.anon_votes.append({"entry_id": entry.id, "type": self.vote})
                    anon_votes_new = self.anon_votes
                else:
                    anon_votes_new.append({"entry_id": entry.id, "type": self.vote})

            self.request.session["anon_votes"] = anon_votes_new

        else:
            sender = self.request.user
            if self.already_voted:
                if prior_cast_up and cast_up:
                    sender.upvoted_entries.remove(entry)
                elif prior_cast_down and cast_down:
                    sender.downvoted_entries.remove(entry)
                elif prior_cast_up and cast_down:
                    sender.upvoted_entries.remove(entry)
                    sender.downvoted_entries.add(entry)
                elif prior_cast_down and cast_up:
                    sender.downvoted_entries.remove(entry)
                    sender.upvoted_entries.add(entry)
            else:
                if cast_up:
                    sender.upvoted_entries.add(entry)
                elif cast_down:
                    sender.downvoted_entries.add(entry)
        return True


class UserAction(AjaxView):
    login_required = True
    require_method = "POST"
    sender = None
    recipient = None

    def handle(self):
        action = self.request_data.get("type")
        self.sender = self.request.user
        self.recipient = get_object_or_404(Author, username=self.request_data.get("recipient_username"))

        if self.sender == self.recipient:
            return self.bad_request()

        if action == "follow":
            return self.follow()
        elif action == "block":
            return self.block()

    def follow(self):
        sender, recipient = self.sender, self.recipient

        if sender in recipient.blocked.all() or recipient in sender.blocked.all():
            return self.bad_request()

        if recipient in sender.following.all():
            sender.following.remove(recipient)
        else:
            sender.following.add(recipient)
        return self.success()

    def block(self):
        sender, recipient = self.sender, self.recipient

        if recipient in sender.blocked.all():
            sender.blocked.remove(recipient)
            return self.success()
        else:
            if recipient in sender.following.all():
                sender.following.remove(recipient)

            if sender in recipient.following.all():
                recipient.following.remove(sender)

            sender.blocked.add(recipient)
            return self.success(redirect_url=self.request.build_absolute_uri(reverse("home")))


class EntryAction(AjaxView):
    login_required = True
    owner_action = False
    redirect_url = None
    entry = None
    success_message = "oldu bu iş"

    def handle(self):
        action = self.request_data.get("type")

        try:
            self.entry = get_object_or_404(Entry, id=int(self.request_data.get("entry_id")))
        except (ValueError, TypeError, Entry.DoesNotExist):
            return self.bad_request()

        self.owner_action = True if self.entry.author == self.request.user else False
        self.redirect_url = reverse_lazy("topic", kwargs={"slug": self.entry.topic.slug}) if self.request_data.get(
            "redirect") == "true" else None

        if action == "delete":
            self.success_message = "silindi"
            return self.delete()

        elif action == "pin":
            return self.pin()

        elif action == "favorite":
            return self.favorite()

        elif action == "favorite_list":
            return self.favorite_list()

        super().handle()

    @ajax_post
    def delete(self):
        if self.owner_action:
            self.entry.delete()
            if self.redirect_url:
                return self.success(message_pop=True, redirect_url=self.redirect_url)
            return self.success()

    @ajax_post
    def pin(self):
        if self.owner_action:
            if self.request.user.pinned_entry == self.entry:  # unpin
                self.request.user.pinned_entry = None
            else:
                self.request.user.pinned_entry = self.entry
            self.request.user.save()
            return self.success()

    @ajax_post
    def favorite(self):
        if self.entry in self.request.user.favorite_entries.all():
            self.request.user.favorite_entries.remove(self.entry)
            self.entry.update_vote(vote_rates["reduce"])
            status = -1
        else:
            self.request.user.favorite_entries.add(self.entry)
            self.entry.update_vote(vote_rates["increase"])
            status = 1

        return JsonResponse({'count': self.entry.favorited_by.count(), 'status': status})

    @ajax_get
    def favorite_list(self):
        users_favorited = self.entry.favorited_by.all()
        authors, novices = [], []
        for user in users_favorited:
            if user.is_novice:
                novices.append(user.username)
            else:
                authors.append(user.username)
        return JsonResponse({'users': [authors, novices]})


class TopicAction(AjaxView):
    login_required = True
    require_method = "POST"
    topic_object = None

    def handle(self):
        action = self.request_data.get("type")

        try:
            self.topic_object = get_object_or_404(Topic, id=int(self.request_data.get("topic_id")))
        except (ValueError, TypeError, ObjectDoesNotExist):
            return self.bad_request()

        if action == "follow":
            return self.follow()

        super().handle()

    def follow(self):
        try:
            # unfollow if already following
            existing = TopicFollowing.objects.get(topic=self.topic_object, author=self.request.user)
            existing.delete()
        except TopicFollowing.DoesNotExist:
            TopicFollowing.objects.create(topic=self.topic_object, author=self.request.user)
        return self.success()

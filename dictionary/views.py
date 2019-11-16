import datetime
import math
import random
from decimal import Decimal

from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Max, Q, Case, When, F, IntegerField
from django.http import Http404, HttpResponseRedirect, JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import View, ListView, UpdateView
from django.views.generic.edit import FormView
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode

from .forms import SignUpForm, EntryForm, SendMessageForm, LoginForm, PreferencesForm, ChangeEmailForm, ResendEmailForm
from .models import Entry, Category, Topic, Author, Message, Conversation, TopicFollowing, Memento, UserVerification
from .util import topic_list_qs, time_threshold_24h, ENTRIES_PER_PAGE, ENTRIES_PER_PAGE_PROFILE, nondb_categories, \
    vote_rates, require_ajax, find_after_page, mark_read, TOPICS_PER_PAGE, YEAR_RANGE, send_email_confirmation


# flatpages for about us etc.
# todo imports according to pep8
# todo scrollbar tracking
# todo converation pagenation
# todo: dikkat include eddiğin duplicate olmasın
# Do not use mutable default arguments in Python
# todo: devamını okuyayım
# todo: @csrf_protect @require_POST
# todo note: Q -> OR
# todo karma skor!
# todo hayvan ara !!
# todo: get_or_create for entry cretion topic shit xd
# entry load için paginator kullacağız efendimiz :))
# Some function views are suitable for Class based views, but I'll convert them after I decide that I wont be making
# more changes to these views


def index(request):
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
    return render(request, "conversation_list.html", context={"conversations": conversations})


#
# class ConversationList(ListView, LoginRequiredMixin):
#     model = Conversation
#     paginate_by = 1
#     template_name = "conversation_list.html"
#     context_object_name = "conversations"
#
#     def get_queryset(self):
#         return Conversation.objects.list_for_user(self.request.user)
class UserPreferences(UpdateView, LoginRequiredMixin):
    model = Author
    form_class = PreferencesForm
    template_name = "user_preferences.html"

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        django_messages.add_message(self.request, django_messages.INFO, "kaydettik efendim")
        return reverse("user_preferences")

    def form_invalid(self, form):
        django_messages.add_message(self.request, django_messages.INFO, "bir şeyler ters gitti")
        return super().form_invalid(form)


class ActivityList(ListView, LoginRequiredMixin):
    model = TopicFollowing
    template_name = "activity.html"
    context_object_name = "topics_following"

    # todo from onread anchor link
    def get_queryset(self):
        return TopicFollowing.objects.filter(author=self.request.user).annotate(
            latest=Max("topic__entry__date_created"),
            is_read=Case(When(Q(latest__gt=F("read_at")), then=1), When(Q(latest__lt=F("read_at")), then=2),
                         output_field=IntegerField()), ).order_by("is_read", "-read_at")


class CategoryList(ListView):
    model = Category
    template_name = "category_list.html"
    context_object_name = "categories"


class EntryUpdate(UpdateView, LoginRequiredMixin):
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
    return render(request, "conversation.html", context=data)


@require_ajax
@login_required
def _compose_message(request):
    message_body = request.POST.get("message_body")
    if len(message_body) < 1:
        return JsonResponse({"success": False, "detail": "az bişeyler yaz yeğen"}, )

    try:
        recipient = Author.objects.get(username=request.POST.get("recipient"))
    except ObjectDoesNotExist:
        return JsonResponse({"success": False, "detail": "öyle bir insan yok etrafta"})

    msg = Message.objects.compose(request.user, recipient, message_body)
    if not msg:
        return JsonResponse({"success": False, "detail": "mesajınızı gönderemedik ne yazık ki"})

    return JsonResponse({"success": True, "detail": "mesajınız sağ salim gönderildi"})


class TopicList(ListView):
    model = Topic
    context_object_name = "topics"
    template_name = "topic_list.html"
    paginate_by = TOPICS_PER_PAGE

    def get_queryset(self):
        year = None
        if self.kwargs["slug"] == "tarihte-bugun":

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
        # todo extend caching support for mobile
        return topic_list_qs(self.request, self.kwargs['slug'], year, extend=True)

    def get_context_data(self, **kwargs):
        slug = self.kwargs['slug']
        nondb_safename = {"bugun": "bugün", "gundem": "gündem", "basiboslar": "başıboşlar",
                          "tarihte-bugun": "tarihte bugün", "kenar": "kenar", "caylaklar": "çaylaklar"}
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
        return context


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


class Logout(LogoutView, LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        success_message = "başarıyla çıkış yaptınız efendim"
        django_messages.add_message(self.request, django_messages.INFO, success_message)
        return super().dispatch(request)


class ChangePassword(PasswordChangeView):
    success_url = reverse_lazy("user_preferences")
    template_name = "user_preferences_password.html"

    def form_valid(self, form):
        django_messages.add_message(self.request, django_messages.INFO, "işlem tamam")
        return super().form_valid(form)


class ChangeEmail(LoginRequiredMixin, FormView):
    template_name = "user_preferences_email.html"
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

    return render(request, "user_profile.html", context=data)


def topic(request, slug=None, entry_id=0, unicode=None):
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


def _autocomplete(request):
    """
    Header search autocomplete filters.
        Problem: Cannot return querysets with length restrictions on 'query' (autocomplete results won't appear),
     if you know how to fix this, please do.
    # TODO: LIST COMPREHENDSIONS
     Todo: also add some users on topic autocomplete.
     """

    if request.GET.get("author"):
        objects = Author.objects.filter(username__istartswith=request.GET.get("author"))
        response = [obj.username for obj in objects]
        return JsonResponse({"suggestions": response})

    query = request.GET.get("query")
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


@login_required
def _favorite(request):
    """
        1. POST for Favorite or unfavorite entries.
        2. GET for favorite count & list.
    """

    if request.method == "GET":
        entry_id = request.GET.get("entry_id")
        try:
            entry = get_object_or_404(Entry, id=entry_id)
        except ValueError:
            return HttpResponse(status=400)
        if entry:
            users_favorited = entry.favorited_by.all()
            authors, novices = [], []
            for user in users_favorited:
                if user.is_novice:
                    novices.append(user.username)
                else:
                    authors.append(user.username)
            return JsonResponse({'users': [authors, novices]})
        return HttpResponse(status=400)

    if request.method == "POST":
        entry_id = request.POST.get("entry_id", None)
        try:
            entry_to_fav = get_object_or_404(Entry, id=entry_id)
        except ValueError:
            return HttpResponse(status=400)

        if entry_to_fav:
            if request.user in entry_to_fav.favorited_by.all():
                request.user.favorite_entries.remove(entry_to_fav)
                entry_to_fav.update_vote(vote_rates['reduce'])
                return JsonResponse({'count': entry_to_fav.favorited_by.count(), 'status': -1})

            request.user.favorite_entries.add(entry_to_fav)
            entry_to_fav.update_vote(vote_rates['increase'])
            return JsonResponse({'count': entry_to_fav.favorited_by.count(), 'status': 1})
    return HttpResponse(status=400)


@require_ajax
def _category(request, slug):
    year = request.GET.get("year", None) if slug == "tarihte-bugun" else None
    if year:
        try:
            if not int(year) in YEAR_RANGE:
                return HttpResponseBadRequest()
        except (ValueError, OverflowError):
            return HttpResponseBadRequest()

    # Caching of "bugun", needs testing
    # reference https://stackoverflow.com/a/20146767/
    if slug == "bugun" and request.user.is_authenticated:
        user_id = request.user.id  # anonymous users are not allowed to view 'bugun'
        # cache keys for 'bugun' cache
        cache_key_normal = f"bugun_{user_id}"
        cache_key_extended = f"bugun_extended_{user_id}"

        is_extended = True if request.GET.get("extended") == "yes" else False
        cached = False if request.GET.get("nocache") == "yes" else True  # returning cached info is OK or not
        cache_key = cache_key_extended if is_extended else cache_key_normal

        if cached and cache.get(cache_key):
            """
            There is cached data, return that. refresh_count informs the
            user about the new data count from the latest caching time.
            """
            data = cache.get(cache_key)
            refresh_count = Entry.objects.filter(date_created__gte=data.get("set_at")).count()

            return JsonResponse({"topic_data": data.get("response"), "refresh_count": refresh_count}, safe=False)

        else:
            # No cached data found, so create cache information to be used the next time.
            cache.delete_many([cache_key_normal, cache_key_extended])
            response = topic_list_qs(request, slug, year)
            cache_data = {"response": response, "set_at": timezone.now()}
            cache.set(cache_key, cache_data, 3000)  # cache at 5 minutes
            return JsonResponse({"topic_data": response}, safe=False)

    response = topic_list_qs(request, slug, year)
    return JsonResponse({"topic_data": response}, safe=False)


@csrf_exempt
@require_ajax
@require_POST
def _vote(request):
    """
    Anonymous users can vote, in order to hinder duplicate votings, session is used; though it is not
    the best way to handle this, I think it's better than storing all the IP adresses of the guest users as acquiring an
    IP adress is a nuance; it depends on the server and it can also be manipulated by keen hackers. It's just better to
    stick to this way instead of making things complicated as there is no way to make this work 100% intended.
    """

    vote = request.POST.get("vote")

    if vote not in ["up", "down"]:
        raise Http404

    try:
        entry = get_object_or_404(Entry, id=int(request.POST.get("entry_id", None)))
    except ValueError:
        raise Http404

    reduce = vote_rates["reduce"]
    increase = vote_rates["increase"]
    sender = request.user

    # self-vote not allowed
    if entry.author == sender:
        raise Http404

    if sender.is_authenticated:
        up = True if vote == "up" else False  # upvoted
        down = True if vote == "down" else False  # downvoted
        upvoters = entry.upvoted_by.all()
        downvoters = entry.downvoted_by.all()

        if sender in upvoters and up:  # cancel upvote
            sender.upvoted_entries.remove(entry)
            entry.update_vote(reduce)
        elif sender in downvoters and down:  # cancel downvote
            sender.downvoted_entries.remove(entry)
            entry.update_vote(increase)
        elif sender in upvoters and down:  # change vote from up to down
            sender.upvoted_entries.remove(entry)
            sender.downvoted_entries.add(entry)
            entry.update_vote(reduce, change=True)
        elif sender in downvoters and up:  # change vote from down to up
            sender.downvoted_entries.remove(entry)
            sender.upvoted_entries.add(entry)
            entry.update_vote(increase, change=True)
        else:  # first time voting
            if up:
                sender.upvoted_entries.add(entry)
                entry.update_vote(increase)
            elif down:
                sender.downvoted_entries.add(entry)
                entry.update_vote(reduce)
        return HttpResponse(status=200)

    else:
        # Anonymous voting
        anon_votes = request.session.get("anon_votes")
        anon_already_voted = False
        anon_already_voted_type = None
        anon_votes_new = []
        k = vote_rates["anonymous_multiplier"]  # so as to make anonymous votes less effective as they are not reliable

        if anon_votes:
            for obj in anon_votes:
                if obj.get("entry_id") == entry.id:
                    anon_already_voted = True
                    anon_already_voted_type = obj.get("type")

        if anon_already_voted:
            if anon_already_voted_type == vote:
                # Removes the vote cast.
                if vote == "up":
                    entry.update_vote(reduce * k)
                elif vote == "down":
                    entry.update_vote(increase * k)
                anon_votes_new = [y for y in anon_votes if y.get('entry_id') != entry.id]
            else:
                # Changes the vote cast.
                if vote == "up":
                    entry.update_vote(increase * k, change=True)
                if vote == "down":
                    entry.update_vote(reduce * k, change=True)

                anon_votes_new = [y for y in anon_votes if y.get('entry_id') != entry.id]
                anon_votes_new.append({"entry_id": entry.id, "type": vote})
        else:
            # First time voting.
            if vote == "up":
                entry.update_vote(increase * k)
            elif vote == "down":
                entry.update_vote(reduce * k)

            if anon_votes:
                anon_votes.append({"entry_id": entry.id, "type": vote})
                anon_votes_new = anon_votes
            else:
                anon_votes_new.append({"entry_id": entry.id, "type": vote})

        request.session["anon_votes"] = anon_votes_new
        return HttpResponse(status=200)


@require_POST
@login_required
@require_ajax
def _user_actions(request):
    action = request.POST.get("type")
    sender = Author.objects.get(id=request.user.id)
    recipient = get_object_or_404(Author, username=request.POST.get("recipient_username"))
    if sender == recipient:
        return HttpResponse(status=403)

    if action in ["follow", "block"]:
        if action == "follow":
            if sender in recipient.blocked.all() or recipient in sender.blocked.all():
                return HttpResponse(status=403)
            if recipient in sender.following.all():
                sender.following.remove(recipient)
            else:
                sender.following.add(recipient)
        elif action == "block":
            if recipient in sender.blocked.all():
                sender.blocked.remove(recipient)
            else:
                if recipient in sender.following.all():
                    sender.following.remove(recipient)

                if sender in recipient.following.all():
                    recipient.following.remove(sender)

                sender.blocked.add(recipient)
                return JsonResponse({"redirect": request.build_absolute_uri(reverse("home"))})

        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)


@require_POST
@require_ajax
@login_required
def _entry_actions(request):
    action = request.POST.get("type")

    try:
        entry = get_object_or_404(Entry, id=int(request.POST.get("entry_id")))
    except ValueError:
        return HttpResponse(status=403)

    redirect_to = reverse_lazy("topic", kwargs={"slug": entry.topic.slug}) if request.POST.get(
        "redirect") == "true" else None

    if action in ["delete", "pin"]:
        if action == "delete":
            if entry.author == request.user:
                entry.delete()
        elif action == "pin":
            if entry.author == request.user:
                if request.user.pinned_entry == entry:
                    request.user.pinned_entry = None
                else:
                    request.user.pinned_entry = entry
                request.user.save()

        if redirect_to:
            django_messages.add_message(request, django_messages.INFO, "oldu bu iş")
            return JsonResponse({"redirect_to": redirect_to})
        else:
            return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)


@require_POST
@require_ajax
@login_required
def _topic_actions(request):
    action = request.POST.get("type")
    try:
        topic_obj = get_object_or_404(Topic, id=int(request.POST.get("topic_id")))
    except ValueError:
        return HttpResponseBadRequest()

    if action == "follow":
        try:
            # unfollow if already following
            existing_obj = TopicFollowing.objects.get(topic=topic_obj, author=request.user)
            existing_obj.delete()
        except TopicFollowing.DoesNotExist:
            TopicFollowing.objects.create(topic=topic_obj, author=request.user)
        return HttpResponse(status=200)

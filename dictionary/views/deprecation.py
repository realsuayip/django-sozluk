import datetime
import math

from django.contrib import messages as notifications
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from ..forms.edit import EntryForm
from ..models import Entry, Topic, Author, TopicFollowing
from ..utils.settings import ENTRIES_PER_PAGE, time_threshold_24h
from ..deprecated_util import find_after_page, mark_read


# flatpages for about us etc.
# todo scrollbar tracking
# todo karma skor!
# todo hayvan ara !!
# ALL views will be converted to class based views.

def index(request):
    return render(request, "index.html")


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

    # handling of: valid slugs with parameters "day", "year (tarihte-bugun)"
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
                        notifications.add_message(request, notifications.INFO,
                                                    "pek bişey bulamadım açıkçası, buyrun hepsi")
                        return redirect("topic", slug=topic_object.slug)
                    else:
                        mark_read(topic_object, request.user)
                        look_for_before = True
                        notifications.add_message(request, notifications.INFO, f"{entries.count()} tane entry")

            elif mode == "caylaklar":
                look_for_before = True
                look_for_after = True
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
            notifications.add_message(request, notifications.INFO, "kenara attık onu")
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

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _, ngettext

from graphene import ID, Int, Mutation, String

from dictionary.conf import settings
from dictionary.models import Category, Suggestion, Topic
from dictionary.utils import time_threshold

from dictionary_graph.utils import login_required


class FollowCategory(Mutation):
    class Arguments:
        pk = ID()

    feedback = String()

    @staticmethod
    @login_required
    def mutate(_root, info, pk):
        category = get_object_or_404(Category.objects, id=pk)
        following = info.context.user.following_categories

        if following.filter(pk=pk).exists():
            following.remove(category)
            return FollowCategory(feedback=_("the channel is no longer followed"))

        following.add(category)
        return FollowCategory(_("the channel is now followed"))


class SuggestCategory(Mutation):
    class Arguments:
        topic = String()
        category = String()
        direction = Int()

    feedback = String()

    @staticmethod
    @login_required
    def mutate(_root, info, topic, category, direction):
        topic = get_object_or_404(Topic, slug=topic)

        if not all(
            (
                direction in (-1, 1),
                info.context.user.is_accessible,
                not info.context.user.is_novice,
                info.context.user.has_perm("dictionary.can_suggest_categories"),
                topic.allow_suggestions,
            )
        ):
            raise ValueError(_("we couldn't handle your request. try again later."))

        suggestion_count_today = Suggestion.objects.filter(
            author=info.context.user, date_created__gte=time_threshold(hours=24)
        ).count()

        if suggestion_count_today >= settings.SUGGESTIONS_PER_DAY:
            raise ValueError(_("you have used up all the suggestion claims you have today. try again later."))

        category = get_object_or_404(Category.objects_all, slug=category)
        kwargs = {"author": info.context.user, "topic": topic, "category": category}

        try:
            obj = Suggestion.objects.get(direction=direction, **kwargs)
            obj.delete()
        except Suggestion.DoesNotExist:
            obj, created = Suggestion.objects.update_or_create(defaults={"direction": direction}, **kwargs)

            kwargs.pop("category")
            if created and Suggestion.objects.filter(**kwargs).count() > settings.SUGGESTIONS_PER_TOPIC:
                obj.delete()
                raise ValueError(
                    ngettext(
                        "you can only suggest %(count)d channel per topic.",
                        "you can only suggest %(count)d channels per topic.",
                        settings.SUGGESTIONS_PER_TOPIC,
                    )
                    % {"count": settings.SUGGESTIONS_PER_TOPIC}
                )

        return SuggestCategory()

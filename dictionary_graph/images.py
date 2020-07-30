from graphene import ObjectType
from graphene import Mutation, String

from dictionary.models import Image

from .utils import login_required


class DeleteImage(Mutation):
    """Meta class for entry action mutations."""

    class Arguments:
        slug = String()

    feedback = String()

    @staticmethod
    @login_required
    def mutate(_root, info, slug):
        image = Image.objects.get(author=info.context.user, slug=slug)
        image.is_deleted = True
        image.save()
        return DeleteImage(feedback=None)


class ImageMutations(ObjectType):
    delete = DeleteImage.Field()

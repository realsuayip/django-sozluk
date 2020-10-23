from graphene import ObjectType
from graphene import Mutation, String

from dictionary.models import Image

from dictionary_graph.utils import login_required


class DeleteImage(Mutation):
    class Arguments:
        slug = String()

    feedback = String()

    @staticmethod
    @login_required
    def mutate(_root, info, slug):
        image = Image.objects.get(author=info.context.user, is_deleted=False, slug=slug)
        image.is_deleted = True
        image.save(update_fields=["is_deleted"])
        return DeleteImage(feedback=None)


class ImageMutations(ObjectType):
    delete = DeleteImage.Field()

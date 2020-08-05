from django.db import models


class CategoryManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(is_pseudo=True)


class CategoryManagerAll(models.Manager):
    pass

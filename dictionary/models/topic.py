from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.shortcuts import reverse

from uuslug import uuslug

from ..utils import turkish_lower
from .author import Author
from .category import Category
from .m2m import TopicFollowing
from .managers.topic import TopicManager, TopicManagerPublished


TOPIC_TITLE_VALIDATORS = [
    RegexValidator(
        r"""^[a-z0-9 ğçıöşü#₺&@()_+=':%/",.!?~\[\]{}<>^;\\|-]+$""",
        message="bu başlık tanımı geçersiz karakterler içeriyor",
    ),
    MaxLengthValidator(50, message="bu başlık çok uzun"),
]


class Topic(models.Model):
    title = models.CharField(
        max_length=50,
        unique=True,
        validators=TOPIC_TITLE_VALIDATORS,
        verbose_name="Başlığın tanımı",
        help_text="Başlık oluşturulduktan sonra tanımını değiştirmek için başlık taşıma özelliğini kullanmalısınız.",
    )

    slug = models.SlugField(max_length=96, unique=True, editable=False)

    created_by = models.ForeignKey(
        Author,
        null=True,
        editable=False,
        on_delete=models.SET_NULL,
        verbose_name="İlk entry giren kullanıcı",
        help_text="Bu başlığa ilk kez halka açık bir şekilde entry giren yazar veya çaylak.",
    )

    category = models.ManyToManyField(Category, blank=True, verbose_name="Kanallar")
    wishes = models.ManyToManyField("Wish", blank=True, editable=False, verbose_name="Ukteler")

    mirrors = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name="Başlık ayrımı",
        help_text="<p style='color: #ba2121'><b>Dikkat!</b> Girdiğiniz başlıklara otomatik olarak başlık ayrımı"
        " eklenecek. Bu nedenle seçtiğiniz bir ana başlık üzerinde çalışmanız önerilir.<br> Bir başlığı ayrımdan"
        " kaldırmak <b>tüm</b> ayrımların silinmesine neden olacaktır; bu nedenle silmek istediğiniz başlık"
        " haricindeki başlıkları tekrar toplu halde eklemek üzere not etmelisiniz.</p>",
    )

    is_banned = models.BooleanField(
        default=False,
        verbose_name="Yasaklı",
        help_text="Yazar ve çaylakların bu başlığa entry girmesini engellemek istiyorsanız işaretleyin.",
    )

    is_censored = models.BooleanField(
        default=False,
        verbose_name="Sansürlü",
        help_text="Bu başlığın sözlük içi aramalarda ve başlık listelerinde gözükmesini istemiyorsanız işaretleyin.",
    )

    is_pinned = models.BooleanField(
        default=False,
        verbose_name="Sabitlenmiş",
        help_text="Bu başlığın gündemde en üstte görünmesini istiyorsanız işaretleyin."
                  " <br>Başlığa en az 1 entry girilmiş olmalı.",
    )

    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Oluşturulma tarihi",
        help_text="<i>Her zaman ilk entry ile örtüşmeyebilir.</i>",
    )

    objects = TopicManager()
    objects_published = TopicManagerPublished()

    def __str__(self):
        return f"{self.title}"

    class Meta:
        permissions = (("move_topic", "başlık taşıyabilir"),)
        verbose_name = "başlık"
        verbose_name_plural = "başlıklar"

    def get_absolute_url(self):
        return reverse("topic", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        self.title = turkish_lower(self.title)
        self.slug = uuslug(self.title, instance=self)
        super().save(*args, **kwargs)

    def follow_check(self, user):
        return TopicFollowing.objects.filter(topic=self, author=user).exists()

    def latest_entry_date(self, sender):
        try:
            return (
                self.entries.exclude(Q(author__in=sender.blocked.all()) | Q(author=sender))
                .latest("date_created")
                .date_created
            )
        except ObjectDoesNotExist:
            return self.date_created

    @property
    def exists(self):
        return True

    @property
    def valid(self):
        return True

    @property
    def has_entries(self):
        return self.entries.exclude(is_draft=True).exists()


class Wish(models.Model):
    author = models.ForeignKey("Author", on_delete=models.CASCADE, related_name="wishes")
    hint = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.__class__.__name__}#{self.pk} u:{self.author.username}"

    class Meta:
        ordering = ("-date_created",)

from django.db import models
from django.shortcuts import reverse
from django.template import defaultfilters
from django.utils import timezone

from uuslug import uuslug


class Announcement(models.Model):
    title = models.CharField(max_length=254, verbose_name="Başlık")
    content = models.TextField(verbose_name="İçerik")
    slug = models.SlugField(editable=False)

    discussion = models.ForeignKey(
        "Topic",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Tartışma başlığı",
        help_text="Opsiyonel. Sözlükteki yazarların bu duyuru hakkında yazacakları başlık.",
    )

    html_only = models.BooleanField(
        default=False,
        verbose_name="HTML açık",
        help_text="Sadece HTML kullanmak için bunu seçin,"
        " aksi halde entry biçimlendirme seçenekleri kullanılabilir.",
    )

    notify = models.BooleanField(
        default=False,
        verbose_name="Kullanıcılara duyur",
        help_text="İşaretlendiği takdirde duyuru yayınlandığı zaman kullanıcılar bildirim alacak.",
    )

    date_edited = models.DateTimeField(null=True, editable=False)
    date_created = models.DateTimeField(
        verbose_name="Yayınlanma tarihi",
        help_text="Yayınlanma tarihini ileriki bir zaman olarak da belirleyebilirsiniz.",
    )

    def __str__(self):
        return f"{self.title} - {defaultfilters.date(timezone.localtime(self.date_created), 'd.m.Y H:i')}"

    def save(self, *args, **kwargs):
        created = self.pk is None

        if created:
            self.slug = uuslug(self.title, instance=self)
        else:
            # Pre-save content check
            previous = Announcement.objects.get(pk=self.pk)

            if previous.content != self.content or previous.title != self.title:
                self.date_edited = timezone.now()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        pub = timezone.localtime(self.date_created)
        return reverse(
            "announcements-detail", kwargs={"year": pub.year, "month": pub.month, "day": pub.day, "slug": self.slug},
        )

    class Meta:
        verbose_name = "duyuru"
        verbose_name_plural = "duyurular"

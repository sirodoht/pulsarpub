import base64

import mistune
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse

from main import validators


class User(AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text="This is your subdomain. Lowercase alphanumeric.",
        validators=[
            validators.AlphanumericHyphenValidator(),
            validators.HyphenOnlyValidator(),
        ],
        error_messages={"unique": "A user with that username already exists."},
    )
    email = models.EmailField(unique=True)
    custom_domain = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        validators=[validators.validate_domain_name],
    )
    custom_css = models.TextField("Custom CSS", blank=True, null=True, default="")
    contact = models.BooleanField("Enable Contact page", default=False)

    website_title = models.CharField(max_length=500, blank=True, null=True)
    homepage = models.TextField(blank=True, null=True, default="")
    show_nav = models.BooleanField(default=True)

    # subscription fields
    is_premium = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    subscription_start_date = models.DateTimeField(blank=True, null=True)
    subscription_end_date = models.DateTimeField(blank=True, null=True)

    @property
    def blog_url(self):
        return f"{settings.PROTOCOL}//{self.username}.{settings.CANONICAL_HOST}"

    @property
    def homepage_as_html(self):
        markdown = mistune.create_markdown(
            escape=False,
            plugins=["task_lists", "footnotes"],
        )
        return markdown(self.homepage)

    def __str__(self):
        return self.username


class Page(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.CharField(
        max_length=300,
        validators=[validators.AlphanumericHyphenValidator()],
        help_text="Lowercase letters, numbers, and - (hyphen) allowed.",
    )
    title = models.CharField(max_length=300)
    body = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    @property
    def body_as_html(self):
        markdown = mistune.create_markdown(
            escape=False,
            plugins=["task_lists", "footnotes"],
        )
        return markdown(self.body)

    def __str__(self):
        return self.title

    class Meta:
        unique_together = [["slug", "user"]]


class Image(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=300)  # original filename
    slug = models.CharField(max_length=300, unique=True)
    data = models.BinaryField()
    extension = models.CharField(max_length=10)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        return self.slug + "." + self.extension

    @property
    def data_as_base64(self):
        return base64.b64encode(self.data).decode("utf-8")

    @property
    def data_size(self):
        """Get image size in MB."""
        return round(len(self.data) / (1024 * 1024), 2)

    def get_raw_absolute_url(self):
        path = reverse(
            "image_raw", kwargs={"slug": self.slug, "extension": self.extension}
        )
        return f"{settings.PROTOCOL}//{settings.CANONICAL_HOST}{path}"

    def get_absolute_url(self):
        path = reverse("image_detail", kwargs={"slug": self.slug})
        return f"{settings.PROTOCOL}//{settings.CANONICAL_HOST}{path}"

    def __str__(self):
        return self.name

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm as DjUserCreationForm
from django.core import validators as dj_validators

from main import models


class UserCreationForm(DjUserCreationForm):
    class Meta:
        model = get_user_model()
        fields = ["username", "email", "website_title"]


class UserUpdateForm(forms.ModelForm):
    home = forms.ModelChoiceField(
        queryset=models.Page.objects.all(),
        required=False,
        empty_label="No home page",
    )

    class Meta:
        model = get_user_model()
        fields = [
            "username",
            "email",
            "website_title",
            "custom_domain",
            "contact",
            "home",
        ]


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, list | tuple):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class UploadImagesForm(forms.Form):
    file = MultipleFileField(
        validators=[
            dj_validators.FileExtensionValidator(["jpeg", "jpg", "png", "gif", "webp"])
        ],
    )


class ContactForm(forms.Form):
    name = forms.CharField()
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)

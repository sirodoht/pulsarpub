import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView as DjLogoutView
from django.core.exceptions import PermissionDenied
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    UpdateView,
)

from main import forms, models


@login_required
def landing(request):
    """
    Landing view for the convenience of logged in users only.
    """
    return render(request, "main/landing.html")


def index(request):
    # Account site mode as reader/enduser
    if hasattr(request, "subdomain"):
        if models.User.objects.filter(username=request.subdomain).exists():
            return render(
                request,
                "main/landing.html",
                {
                    "canonical_url": f"{settings.PROTOCOL}//{settings.CANONICAL_HOST}",
                    "subdomain": request.subdomain,
                    "account_user": request.account_user,
                    "page_list": models.Page.objects.filter(
                        user=request.account_user
                    ).defer("body"),
                },
            )
        else:
            return redirect("//" + settings.CANONICAL_HOST + reverse("index"))

    # Account site as owner:
    # Redirect to "account_index" so that the requests gets a subdomain
    if request.user.is_authenticated:
        return redirect(
            f"//{request.user.username}.{settings.CANONICAL_HOST}{reverse('index')}"
        )

    # Landing site as non-logged-in user
    return render(request, "main/landing.html")


def domain_check(request):
    """
    This view returns 200 if domain given exists as custom domain in any user account.
    """
    url = request.GET.get("domain")
    if not url:
        raise PermissionDenied()

    # Landing case
    if url == settings.CANONICAL_HOST:
        return HttpResponse()

    # Custom domain case, can by anything
    if models.User.objects.filter(custom_domain=url).exists():
        return HttpResponse()

    # Subdomain case, can only by <username>.dukkha.pub
    if len(url.split(".")) != 3:
        raise PermissionDenied()

    username = url.split(".")[0]
    if models.User.objects.filter(username=username).exists():
        return HttpResponse()

    raise PermissionDenied()


def markdown(request):
    return render(request, "main/markdown.html")


# Users and user settings


class UserCreate(CreateView):
    form_class = forms.UserCreationForm
    success_message = "welcome :)"
    success_url = reverse_lazy("index")
    template_name = "main/user_create.html"

    def form_valid(self, form):
        self.object = form.save()
        user = authenticate(
            username=form.cleaned_data.get("username"),
            password=form.cleaned_data.get("password1"),
        )
        login(self.request, user)
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())


class Logout(DjLogoutView):
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "logged out")
        return super().dispatch(request, *args, **kwargs)


class UserUpdate(LoginRequiredMixin, UpdateView):
    form_class = forms.UserUpdateForm
    success_url = reverse_lazy("user_update")
    template_name = "main/user_update.html"

    def get_object(self):
        return self.request.user

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["home"].queryset = models.Page.objects.filter(
            user=self.request.user
        )
        return form


class CSSUpdate(LoginRequiredMixin, UpdateView):
    model = models.User
    fields = ["custom_css"]
    template_name = "main/custom_css.html"
    success_url = reverse_lazy("css_update")

    def get_object(self):
        return self.request.user


@login_required
def dashboard(request):
    if hasattr(request, "subdomain"):
        return redirect("//" + settings.CANONICAL_HOST + reverse("dashboard"))

    return render(
        request,
        "main/dashboard.html",
        {
            "page_list": models.Page.objects.filter(user=request.user),
            "blog_url": request.user.blog_url,
        },
    )


# Pages


class PageCreate(LoginRequiredMixin, CreateView):
    model = models.Page
    fields = ["title", "slug", "body"]
    template_name = "main/page_create.html"

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("page_detail", args=(self.object.slug,))


class PageDetail(DetailView):
    model = models.Page

    def get_success_url(self):
        return reverse("page_detail", args=(self.object.slug,))

    def get_queryset(self):
        return models.Page.objects.filter(user__username=self.request.subdomain)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["canonical_url"] = f"{settings.PROTOCOL}//{settings.CANONICAL_HOST}"
        if hasattr(self.request, "subdomain"):
            context["account_user"] = self.request.account_user
            context["page_list"] = models.Page.objects.filter(
                user__username=self.request.subdomain
            )
        return context

    def dispatch(self, request, *args, **kwargs):
        if hasattr(request, "subdomain"):
            return super().dispatch(request, *args, **kwargs)

        if request.user.is_authenticated:
            subdomain = request.user.username
            return redirect(
                f"{settings.PROTOCOL}//{subdomain}.{settings.CANONICAL_HOST}{request.path}"
            )
        else:
            return redirect("index")


class PageUpdate(LoginRequiredMixin, UpdateView):
    model = models.Page
    fields = ["title", "slug", "body"]
    template_name = "main/page_update.html"

    def get_success_url(self):
        return reverse("page_detail", args=(self.object.slug,))

    def get_queryset(self):
        return models.Page.objects.filter(user__username=self.request.subdomain)

    def form_valid(self, form):
        if (
            models.Page.objects.filter(
                user=self.request.user, slug=form.cleaned_data.get("slug")
            )
            .exclude(id=self.object.id)
            .exists()
        ):
            form.add_error("slug", "This slug is already defined as one of your pages.")
            return self.render_to_response(self.get_context_data(form=form))
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        page = self.get_object()
        if request.user != page.user:
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)


class PageDelete(LoginRequiredMixin, DeleteView):
    model = models.Page
    success_url = reverse_lazy("index")

    def get_queryset(self):
        return models.Page.objects.filter(user__username=self.request.subdomain)

    def dispatch(self, request, *args, **kwargs):
        page = self.get_object()
        if request.user != page.user:
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)


# Images


class ImageList(LoginRequiredMixin, FormView):
    form_class = forms.UploadImagesForm
    template_name = "main/image_list.html"
    success_url = reverse_lazy("image_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["image_list"] = models.Image.objects.filter(user=self.request.user)

        context["total_quota"] = 0
        for image in models.Image.objects.filter(user=self.request.user):
            context["total_quota"] += image.data_size
        context["total_quota"] = round(context["total_quota"], 2)
        return context

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist("file")
        if form.is_valid():
            for f in files:
                name_ext_parts = f.name.rsplit(".", 1)
                name = name_ext_parts[0].replace(".", "-")
                self.extension = name_ext_parts[1].casefold()
                if self.extension == "jpg":
                    self.extension = "jpeg"
                data = f.read()

                # Image file limit 1.1MB = 1.1 * 1000^2
                if len(data) > 1.1 * 1000 * 1000:
                    form.add_error("file", "File too big. Limit is 1MB.")
                    return self.form_invalid(form)

                self.slug = str(uuid.uuid4())[:8]
                models.Image.objects.create(
                    name=name,
                    data=data,
                    extension=self.extension,
                    user=request.user,
                    slug=self.slug,
                )
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        # if ?raw=true in url, return to image_raw instead of image_list
        if (
            len(self.request.FILES.getlist("file")) == 1
            and self.request.GET.get("raw") == "true"
        ):
            return reverse("image_raw", args=(self.slug, self.extension))
        else:
            return str(self.success_url)  # success_url is lazy

    def form_invalid(self, form):
        # if ?raw=true in url, return form error as string
        if (
            len(self.request.FILES.getlist("file")) == 1
            and self.request.GET.get("raw") == "true"
        ):
            return HttpResponseBadRequest(" ".join(form.errors["file"]))
        else:
            return super().form_invalid(form)


class ImageDetail(LoginRequiredMixin, DetailView):
    model = models.Image

    def dispatch(self, request, *args, **kwargs):
        image = self.get_object()
        if request.user != image.user:
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)


async def image_raw(request, slug, extension):
    image = await models.Image.objects.filter(slug=slug).afirst()
    if not image or extension != image.extension:
        raise Http404()
    return HttpResponse(image.data, content_type="image/" + image.extension)


class ImageUpdate(LoginRequiredMixin, UpdateView):
    model = models.Image
    fields = ["name"]
    template_name = "main/image_edit.html"

    def dispatch(self, request, *args, **kwargs):
        image = self.get_object()
        if request.user != image.user:
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)


class ImageDelete(LoginRequiredMixin, DeleteView):
    model = models.Image
    success_url = reverse_lazy("image_list")

    def dispatch(self, request, *args, **kwargs):
        image = self.get_object()
        if request.user != image.user:
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)


# Contact


class Contact(FormView):
    form_class = forms.ContactForm
    template_name = "main/contact.html"
    success_url = reverse_lazy("index")
    success_message = "message has been sent, thank you"

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            # TODO: Email account user with message info
            messages.success(self.request, self.success_message)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self.request, "subdomain"):
            context["account_user"] = self.request.account_user
            context["page_list"] = models.Page.objects.filter(
                user__username=self.request.subdomain
            )
        return context

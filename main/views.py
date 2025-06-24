import json
import logging
import time
import uuid

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.mail import mail_admins
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    TemplateView,
    UpdateView,
)

from main import denylist, forms, models

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


@login_required
def landing(request):
    """
    Landing view for the convenience of logged in users only.
    """
    return render(request, "main/landing.html")


def index(request):
    # check if there is a subdomain already
    if hasattr(request, "subdomain"):  # noqa: SIM102
        # check if subdomain is valid
        if models.User.objects.filter(username=request.subdomain).exists():
            # check if user is logged in and on their own website
            if request.user.is_authenticated and request.user == request.account_user:  # noqa: SIM102
                # check if user has set website title
                if request.user.website_title is None:
                    return redirect("onboarding_title")
            return render(
                request,
                "main/account_index.html",
                {
                    "canonical_url": f"{settings.PROTOCOL}//{settings.CANONICAL_HOST}",
                    "account_user": request.account_user,
                    "page_list": models.Page.objects.filter(
                        user=request.account_user
                    ).defer("body"),
                },
            )

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

    # Subdomain case, can only by <username>.pulsar.pub
    if len(url.split(".")) != 3:
        raise PermissionDenied()

    username = url.split(".")[0]
    if models.User.objects.filter(username=username).exists():
        return HttpResponse()

    raise PermissionDenied()


def markdown(request):
    return render(request, "main/markdown.html")


# Onboarding


class OnboardingTitle(LoginRequiredMixin, UpdateView):
    model = models.User
    fields = ["website_title"]
    template_name = "main/onboarding_title.html"
    success_url = reverse_lazy("onboarding_body")

    def get_object(self):
        return self.request.user


class OnboardingBody(LoginRequiredMixin, UpdateView):
    model = models.User
    fields = ["homepage"]
    template_name = "main/onboarding_body.html"
    success_url = reverse_lazy("onboarding_done")

    def get_object(self):
        return self.request.user


class OnboardingDone(LoginRequiredMixin, TemplateView):
    template_name = "main/onboarding_done.html"


# Users and user settings


class UserCreate(CreateView):
    form_class = forms.UserCreationForm
    success_url = reverse_lazy("onboarding_title")
    template_name = "main/user_create.html"

    def form_valid(self, form):
        if form.cleaned_data["username"] in denylist.DISALLOWED_USERNAMES:
            form.add_error("username", "username unavailable")
            return self.render_to_response(self.get_context_data(form=form))
        self.object = form.save()
        user = authenticate(
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password1"],
        )
        login(self.request, user)
        return HttpResponseRedirect(self.get_success_url())


class UserUpdate(LoginRequiredMixin, UpdateView):
    form_class = forms.UserUpdateForm
    success_url = reverse_lazy("user_update")
    template_name = "main/user_update.html"

    def get_object(self):
        return self.request.user


class CSSUpdate(LoginRequiredMixin, UpdateView):
    model = models.User
    fields = ["custom_css"]
    template_name = "main/custom_css.html"
    success_url = reverse_lazy("index")

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
            "subscription_enabled": bool(settings.STRIPE_SECRET_KEY),
            "website_url": request.user.website_url,
            "page_list": models.Page.objects.filter(user=request.user),
        },
    )


# Index


class IndexBodyUpdate(LoginRequiredMixin, UpdateView):
    model = models.User
    fields = ["homepage"]
    template_name = "main/homepage_update.html"
    success_url = reverse_lazy("index")

    def get_object(self):
        return self.request.user


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
    template_name = "main/image_update.html"

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


# Subscription


@login_required
def subscription_index(request):
    if hasattr(request, "subdomain"):
        return redirect("//" + settings.CANONICAL_HOST + reverse("subscription_index"))

    return render(
        request,
        "main/subscription_index.html",
        {
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "user": request.user,
        },
    )


@login_required
@require_POST
def create_checkout_session(request):
    if request.user.is_premium:
        messages.info(request, "You already have an active premium subscription.")
        return redirect("subscription_index")

    try:
        if not request.user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                metadata={
                    "user_id": request.user.id,
                    "username": request.user.username,
                },
            )
            request.user.stripe_customer_id = customer.id
            request.user.save()
        else:
            customer = stripe.Customer.retrieve(request.user.stripe_customer_id)
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": settings.STRIPE_PRICE_ID,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=request.build_absolute_uri(reverse("subscription_success")),
            cancel_url=request.build_absolute_uri(reverse("subscription_index")),
        )
        return redirect(checkout_session.url)
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        messages.error(
            request, "error processing your request, please contact admin@pulsar.pub"
        )
        return redirect("subscription_index")


@login_required
def subscription_success(request):
    messages.success(request, "thanks for subscribing!")
    time.sleep(2)
    return redirect("subscription_index")


@login_required
def subscription_cancel(request):
    if request.method == "POST":
        form = forms.CancelSubscriptionForm(request.POST)
        if form.is_valid():
            try:
                if request.user.stripe_subscription_id:
                    # cancel at period end
                    stripe.Subscription.modify(
                        request.user.stripe_subscription_id, cancel_at_period_end=True
                    )
                    messages.success(
                        request,
                        "your subscription will end at the end of the current billing period and will not renew",
                    )
                else:
                    messages.error(request, "no active subscription found")
            except Exception as e:
                logger.error(f"Error canceling subscription: {e}")
                messages.error(
                    request,
                    "there was an error canceling your subscription. please contact admin@pulsar.pub",
                )
            return redirect("subscription_index")
    else:
        form = forms.CancelSubscriptionForm()

    return render(request, "main/subscription_cancel.html", {"form": form})


@csrf_exempt
@require_POST
def stripe_webhook(request):
    logger.info("Stripe webhook received")
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as e:
        logger.error(f"invalid payload in Stripe webhook: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"invalid signature in Stripe webhook: {e}")
        return HttpResponse(status=400)

    logger.info(f"processing webhook event: {event['type']}")

    # send admin email notifications
    send_webhook_admin_email(event["type"], event)

    if event["type"] == "customer.subscription.created":
        subscription = event["data"]["object"]
        handle_subscription_created(subscription)
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        handle_subscription_updated(subscription)
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        handle_subscription_deleted(subscription)
    elif event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        handle_payment_succeeded(invoice)
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        handle_payment_failed(invoice)
    else:
        logger.info(f"unhandled webhook event type: {event['type']}")

    return HttpResponse(status=200)


def handle_subscription_created(subscription):
    try:
        customer_id = subscription["customer"]
        user = models.User.objects.get(stripe_customer_id=customer_id)

        user.stripe_subscription_id = subscription["id"]
        user.is_premium = subscription["status"] == "active"
        user.subscription_start_date = timezone.datetime.fromtimestamp(
            subscription["created"], tz=timezone.timezone.utc
        )

        if (
            subscription.get("items")
            and subscription["items"].get("data")
            and len(subscription["items"]["data"]) > 0
        ):
            item = subscription["items"]["data"][0]
            if item.get("current_period_end"):
                user.subscription_end_date = timezone.datetime.fromtimestamp(
                    item["current_period_end"], tz=timezone.timezone.utc
                )
        user.save()
        logger.info(f"subscription created for user {user.username}")
    except models.User.DoesNotExist:
        logger.error(f"user not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"error handling subscription created: {e}")


def handle_subscription_updated(subscription):
    try:
        customer_id = subscription["customer"]
        user = models.User.objects.get(stripe_customer_id=customer_id)
        user.is_premium = subscription["status"] == "active"
        if (
            subscription.get("items")
            and subscription["items"].get("data")
            and len(subscription["items"]["data"]) > 0
        ):
            item = subscription["items"]["data"][0]
            if item.get("current_period_end"):
                user.subscription_end_date = timezone.datetime.fromtimestamp(
                    item["current_period_end"], tz=timezone.timezone.utc
                )
        user.save()
        logger.info(f"subscription updated for user {user.username}")
    except models.User.DoesNotExist:
        logger.error(f"user not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"error handling subscription updated: {e}")


def handle_subscription_deleted(subscription):
    try:
        customer_id = subscription["customer"]
        user = models.User.objects.get(stripe_customer_id=customer_id)
        user.is_premium = False
        user.subscription_end_date = timezone.now()
        user.save()
        logger.info(f"subscription deleted for user {user.username}")
    except models.User.DoesNotExist:
        logger.error(f"user not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"error handling subscription deleted: {e}")


def handle_payment_succeeded(invoice):
    try:
        customer_id = invoice["customer"]
        user = models.User.objects.get(stripe_customer_id=customer_id)
        logger.info(f"payment succeeded for user {user.username}")
    except models.User.DoesNotExist:
        logger.error(f"user not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"error handling payment succeeded: {e}")


def handle_payment_failed(invoice):
    try:
        customer_id = invoice["customer"]
        user = models.User.objects.get(stripe_customer_id=customer_id)
        logger.warning(f"payment failed for user {user.username}")
    except models.User.DoesNotExist:
        logger.error(f"user not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"error handling payment failed: {e}")


def send_webhook_admin_email(webhook_type, webhook_data):
    try:
        formatted_data = json.dumps(webhook_data, indent=2, default=str)
        subject = f"Stripe Webhook Received: {webhook_type}"
        message = f"""
A Stripe webhook has been received and processed.

Webhook Type: {webhook_type}
Timestamp: {timezone.now()}

Webhook Data:
{formatted_data}
        """
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=True,  # don't fail the webhook if email fails
        )
        logger.info(f"admin email sent for webhook type: {webhook_type}")
    except Exception as e:
        # no exceptions to avoid breaking webhook processing
        logger.error(f"failed to send admin email for webhook: {e}")

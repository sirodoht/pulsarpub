from django.contrib.auth.views import LogoutView
from django.urls import include, path, re_path

from main import views

urlpatterns = [
    path("", views.index, name="index"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/landing/", views.landing, name="landing"),
    path("dashboard/css/", views.CSSUpdate.as_view(), name="css_update"),
    path(
        "dashboard/homepage/",
        views.IndexBodyUpdate.as_view(),
        name="homepage_update",
    ),
]

# Docs
urlpatterns += [
    path("docs/markdown/", views.markdown, name="markdown"),
]

# Onboarding
urlpatterns += [
    path("onboarding/title/", views.OnboardingTitle.as_view(), name="onboarding_title"),
    path("onboarding/body/", views.OnboardingBody.as_view(), name="onboarding_body"),
    path("onboarding/done/", views.OnboardingDone.as_view(), name="onboarding_done"),
]

# User system
urlpatterns += [
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    path(
        "accounts/create/",
        views.UserCreate.as_view(),
        name="user_create",
    ),
    path("accounts/edit/", views.UserUpdate.as_view(), name="user_update"),
    path("accounts/domain/", views.domain_check, name="domain_check"),
]

# Subscription
urlpatterns += [
    path("subscription/", views.subscription_index, name="subscription_index"),
    path(
        "subscription/checkout/",
        views.create_checkout_session,
        name="create_checkout_session",
    ),
    path(
        "subscription/success/", views.subscription_success, name="subscription_success"
    ),
    path("subscription/cancel/", views.subscription_cancel, name="subscription_cancel"),
    path("webhooks/stripe/", views.stripe_webhook, name="stripe_webhook"),
]

# Images
urlpatterns += [
    path("images/<slug:slug>.<slug:extension>", views.image_raw, name="image_raw"),
    re_path(
        r"^images/list/(?P<options>\?[\w\=]+)?$",  # e.g. images/ or images/?raw=true
        views.ImageList.as_view(),
        name="image_list",
    ),
    path("images/<slug:slug>/", views.ImageDetail.as_view(), name="image_detail"),
    path("images/<slug:slug>/edit/", views.ImageUpdate.as_view(), name="image_update"),
    path(
        "images/<slug:slug>/delete/",
        views.ImageDelete.as_view(),
        name="image_delete",
    ),
]

# Pages
# This section needs to be last due to <slug> being the first word in the path
urlpatterns += [
    path("new/page/", views.PageCreate.as_view(), name="page_create"),
    path("<slug:slug>/", views.PageDetail.as_view(), name="page_detail"),
    path("<slug:slug>/edit/", views.PageUpdate.as_view(), name="page_update"),
    path("<slug:slug>/delete/", views.PageDelete.as_view(), name="page_delete"),
]

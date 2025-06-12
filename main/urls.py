from django.urls import include, path, re_path

from main import views

urlpatterns = [
    path("", views.index, name="index"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/landing/", views.landing, name="landing"),
    path("css/update/", views.CSSUpdate.as_view(), name="css_update"),
    path("dashboard/markdown/", views.markdown, name="markdown"),
    path("contact/", views.Contact.as_view(), name="contact"),
]

# User system
urlpatterns += [
    path("accounts/logout/", views.Logout.as_view(), name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    path(
        "accounts/create/",
        views.UserCreate.as_view(),
        name="user_create",
    ),
    path("accounts/edit/", views.UserUpdate.as_view(), name="user_update"),
    path("accounts/domain/", views.domain_check, name="domain_check"),
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

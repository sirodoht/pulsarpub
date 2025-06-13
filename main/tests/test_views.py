from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from main import models


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = models.User.objects.create_user(
            username="alice",
            password="password",
            email="alice@example.com",
        )
        self.domain_user = models.User.objects.create_user(
            username="bob",
            password="password",
            email="bob@example.com",
            custom_domain="example.com",
        )
        self.page = models.Page.objects.create(
            user=self.user,
            title="Hello",
            slug="hello",
            body="world",
        )

    def test_index_anonymous_landing(self):
        response = self.client.get(reverse("index"), HTTP_HOST=settings.CANONICAL_HOST)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "main/landing.html")

    def test_index_redirects_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("index"), HTTP_HOST=settings.CANONICAL_HOST)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response["Location"].startswith(
                f"//{self.user.username}.{settings.CANONICAL_HOST}"
            )
        )

    def test_domain_check(self):
        url = reverse("domain_check")
        # canonical host exists
        response = self.client.get(url, {"domain": settings.CANONICAL_HOST})
        self.assertEqual(response.status_code, 200)
        # custom domain exists
        response = self.client.get(url, {"domain": self.domain_user.custom_domain})
        self.assertEqual(response.status_code, 200)
        # subdomain exists
        response = self.client.get(
            url, {"domain": f"{self.user.username}.{settings.CANONICAL_HOST}"}
        )
        self.assertEqual(response.status_code, 200)
        # non existing domain
        response = self.client.get(url, {"domain": "nosuch.domain"})
        self.assertEqual(response.status_code, 403)

    def test_page_detail_subdomain(self):
        response = self.client.get(
            reverse("page_detail", args=(self.page.slug,)),
            HTTP_HOST=f"{self.user.username}.{settings.CANONICAL_HOST}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.page.title)

    def test_page_detail_redirects_without_subdomain(self):
        response = self.client.get(
            reverse("page_detail", args=(self.page.slug,)),
            HTTP_HOST=settings.CANONICAL_HOST,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("index"))

    def test_dashboard_requires_login(self):
        response = self.client.get(
            reverse("dashboard"), HTTP_HOST=settings.CANONICAL_HOST
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_dashboard_subdomain_redirect(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("dashboard"),
            HTTP_HOST=f"{self.user.username}.{settings.CANONICAL_HOST}",
        )
        self.assertEqual(response.status_code, 302)
        expected = f"//{settings.CANONICAL_HOST}{reverse('dashboard')}"
        self.assertEqual(response["Location"], expected)

    def test_dashboard_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("dashboard"), HTTP_HOST=settings.CANONICAL_HOST
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "main/dashboard.html")

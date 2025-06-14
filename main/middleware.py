import logging

from django.conf import settings
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect

from main import models

logger = logging.getLogger(__name__)


def host_middleware(get_response):
    def middleware(request):
        logger.debug("host midd begin")

        # Skip host validation for webhook endpoints
        if request.path.startswith("/webhooks/"):
            logger.debug("host midd: continue for webhook")
            return get_response(request)

        host = request.META.get("HTTP_HOST")
        logger.debug(f"{host=}")

        # No http Host header in testing env.
        if not host:
            logger.debug("no host, testing mode, return")
            return get_response(request)

        host_parts = host.split(".")
        canonical_parts = settings.CANONICAL_HOST.split(".")
        logger.debug(f"{settings.CANONICAL_HOST=}")

        # [1] Handle pulsar.pub landing and dashboard pages. All dashboard pages (ie.
        # all user account settings etc.) are on the root domain.
        # Strategy: don't set request.subdomain, return immediately.
        if host == settings.CANONICAL_HOST:
            if request.user.is_authenticated:
                request.custom_css = request.user.custom_css
            logger.debug("host midd case [1]")
            logger.debug("host == settings.CANONICAL_HOST, return")
            return get_response(request)

        # [2] Local Caddy requests for TLS ask
        elif host == "127.0.0.1:5000":
            logger.debug("host midd case [2]")
            return get_response(request)

        # [3] Handle <subdomain>.pulsar.pub pages.
        # Strategy: Set subdomain to given subdomain.
        elif (
            len(host_parts) == 3
            and host_parts[1] == canonical_parts[0]  # should be "pulsar"
            and host_parts[2] == canonical_parts[1]  # should be "blog"
        ):
            logger.debug("host midd case [3]")

            request.subdomain = host_parts[0]

            # Check if subdomain exists.
            if not models.User.objects.filter(username=request.subdomain).exists():
                raise Http404()

            request.account_user = models.User.objects.get(username=request.subdomain)
            request.custom_css = request.user.custom_css

            # Redirect to custom urls for cases:
            # * Logged out / anon users
            # * Logged in but on other user's subdomain
            if not request.user.is_authenticated or (
                request.user.is_authenticated
                and request.user.username != request.subdomain
            ):
                redir_domain = ""

                # User has set custom domain
                if request.account_user.custom_domain:
                    redir_domain = (
                        request.account_user.custom_domain + request.path_info
                    )

                # Prepend double slashes to indicate other domain if there is no
                # protocol prefix.
                if redir_domain and "://" not in redir_domain:
                    redir_domain = "//" + redir_domain

                if redir_domain:
                    return redirect(redir_domain)

            return get_response(request)

        # [4] Custom domain case
        elif models.User.objects.filter(custom_domain=host).exists():
            logger.debug("host midd case [4]")
            request.account_user = models.User.objects.get(custom_domain=host)
            request.custom_css = request.account_user.custom_css
            request.subdomain = request.account_user.username
            return get_response(request)

        # [5] Bad request
        else:
            return HttpResponseBadRequest()

    return middleware

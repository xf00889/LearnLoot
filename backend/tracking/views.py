from __future__ import annotations

from django.http import Http404, HttpRequest, HttpResponseRedirect
from django.views.decorators.http import require_GET

from courses.public_api import get_public_course_or_404

from .services import (
    OutboundDestinationError,
    record_click_event,
    resolve_outbound_destination,
)


@require_GET
def outbound_redirect(
    request: HttpRequest,
    provider_slug: str,
    course_slug: str,
) -> HttpResponseRedirect:
    course = get_public_course_or_404(provider_slug, course_slug)
    try:
        destination = resolve_outbound_destination(course)
    except OutboundDestinationError as exc:
        raise Http404("Outbound destination unavailable") from exc

    # Analytics is deliberately best-effort. A temporary analytics/cache failure
    # must not strand a visitor after the course and destination have passed the
    # safety checks. No IP address or user-agent is stored in ClickEvent.
    record_click_event(
        request=request,
        course=course,
        destination=destination,
    )

    response = HttpResponseRedirect(destination.url)
    response["Cache-Control"] = "no-store, private"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response

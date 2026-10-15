"""Shared bounded site-read/login retry classification; no login recipe."""
SITE_RETRY_DELAYS = (2, 5, 10)

# Exact adapter codes only. HTTP_REQUEST_FAILED/LOGIN_NOT_READY and generic
# SOURCE_UNAVAILABLE do not prove a transient failure and deliberately stay out.
# LOGIN_NOT_CONFIRMED is emitted after the recipe checks rejection/challenge;
# it means the submitted login did not reach its readiness confirmation.
_TRANSIENT_SITE_FAILURES = frozenset({
    'BROWSER_TIMEOUT', 'LOGIN_PAGE_UNAVAILABLE', 'LOGIN_NOT_CONFIRMED',
    'RESULT_NAVIGATION_FAILED', 'SEARCH_NAVIGATION_FAILED', 'PRODUCT_NAVIGATION_FAILED',
})


def retryable_site_failure(code):
    """Unknown, missing and authorization-related reasons never repeat a login."""
    return isinstance(code, str) and code.strip().upper() in _TRANSIENT_SITE_FAILURES

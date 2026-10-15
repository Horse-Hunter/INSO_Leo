"""Shared bounded site-read/login retry classification; no login recipe."""
SITE_RETRY_DELAYS = (2, 5, 10)


def retryable_site_failure(code):
    code = str(code).upper()
    return not any(token in code for token in (
        'CAPTCHA', 'CHALLENGE', 'VERIFICATION', 'OTP', 'SECURITY_EVENT',
        'CREDENTIALS_UNAVAILABLE', 'CREDENTIAL_NOT_CONFIGURED', 'CREDENTIAL_REJECTED',
        'LOGIN_REJECTED', 'SESSION_IDENTITY_UNVERIFIED', 'SECURITY_EVENT', 'FX',
    ))

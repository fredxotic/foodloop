from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class BurstRateThrottle(UserRateThrottle):
    """
    Throttle for burst requests (short-term).
    Allows 60 requests per minute.
    """
    scope = 'burst'
    rate = '60/min'


class SustainedRateThrottle(UserRateThrottle):
    """
    Throttle for sustained requests (long-term).
    Allows 1000 requests per day.
    """
    scope = 'sustained'
    rate = '1000/day'


class AuthRateThrottle(AnonRateThrottle):
    """
    Throttle for authentication endpoints.
    Allows 5 requests per minute for anonymous users.
    """
    scope = 'auth'
    rate = '5/min'


class UploadRateThrottle(UserRateThrottle):
    """
    Throttle for file upload endpoints.
    Allows 20 uploads per hour.
    """
    scope = 'upload'
    rate = '20/hour'


class EmailRateThrottle(UserRateThrottle):
    """
    Throttle for email sending operations.
    Allows 10 emails per hour per user.
    """
    scope = 'email'
    rate = '10/hour'
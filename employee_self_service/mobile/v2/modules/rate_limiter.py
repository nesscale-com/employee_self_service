import frappe
from datetime import datetime, timedelta
import json

class CustomRateLimiter:
    def __init__(self, limit: int, window: int, user_id: str):
        """
        Initialize the rate limiter.
        :param limit: Number of allowed requests within the time window.
        :param window: Time window in seconds.
        :param user_id: A unique identifier for the user (user ID or IP address).
        """
        self.limit = limit
        self.window = window
        self.user_id = user_id
        self.cache_key = frappe.cache.make_key(f"rate-limit:{self.user_id}")

    def is_allowed(self):
        """
        Check if the request is allowed under the rate limit.
        :return: True if allowed, False otherwise.
        """
        now = datetime.now()
        rate_data = frappe.cache.get(self.cache_key)
        if rate_data:
            # Deserialize the stored rate data
            requests, start_time = json.loads(rate_data)
            start_time = datetime.fromisoformat(start_time)

            # Reset the window if it has expired
            if now - start_time > timedelta(seconds=self.window):
                self.reset(now)
                return True

            # Allow request if within the limit
            if requests < self.limit:
                frappe.cache.set(
                    self.cache_key,
                    json.dumps((requests + 1, start_time.isoformat())),  # Serialize
                    self.window,
                )
                return True
            return False
        else:
            # Initialize rate data for the first request
            self.reset(now)
            return True

    def reset(self, now: datetime):
        """
        Reset the rate limiter for a new window.
        :param now: Current timestamp.
        """
        frappe.cache.set(
            self.cache_key,
            json.dumps((1, now.isoformat())),  # Serialize
            self.window,
        )

    def retry_after(self):
        """
        Calculate the retry-after duration in seconds.
        :return: Seconds until the rate limit resets.
        """
        rate_data = frappe.cache.get(self.cache_key)
        if rate_data:
            _, start_time = json.loads(rate_data)  # Deserialize
            start_time = datetime.fromisoformat(start_time)
            reset_time = start_time + timedelta(seconds=self.window)
            return max(0, (reset_time - datetime.now()).total_seconds())
        return 0
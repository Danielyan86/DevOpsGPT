from flask import request, jsonify
from functools import wraps
from cachetools import TTLCache
import time

# Cache that stores IP addresses and their request counts
request_cache = TTLCache(maxsize=100, ttl=60)  # 60 seconds TTL


def rate_limit(max_requests: int = 10):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr
            current_time = time.time()

            if ip in request_cache:
                requests = request_cache[ip]
                if len(requests) >= max_requests:
                    return jsonify({"error": "Rate limit exceeded"}), 429

                # Add the new request timestamp
                requests.append(current_time)
                request_cache[ip] = requests
            else:
                request_cache[ip] = [current_time]

            return f(*args, **kwargs)

        return decorated_function

    return decorator

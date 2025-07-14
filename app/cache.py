import redis
from app.config import REDIS_HOST, REDIS_PORT

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

def cache_text(key: str, value: str):
    r.set(key, value, ex=3600)  # Cache expires in 1 hour

def get_cached_text(key: str):
    result = r.get(key)
    return result.decode() if result else None

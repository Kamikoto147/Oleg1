import time
from functools import wraps
from typing import Any, Callable, Optional

class SimpleCache:
    """Простой in-memory кэш с TTL"""
    
    def __init__(self, default_ttl: int = 300):  # 5 минут по умолчанию
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Установить значение в кэш"""
        if ttl is None:
            ttl = self.default_ttl
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
    
    def delete(self, key: str) -> None:
        """Удалить значение из кэша"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self) -> None:
        """Очистить весь кэш"""
        self.cache.clear()
    
    def cleanup_expired(self) -> None:
        """Удалить истекшие записи"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self.cache.items()
            if current_time >= expiry
        ]
        for key in expired_keys:
            del self.cache[key]

# Глобальный экземпляр кэша
cache = SimpleCache()

def cached(ttl: int = 300, key_prefix: str = ""):
    """Декоратор для кэширования результатов функций"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем ключ кэша
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Пытаемся получить из кэша
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Выполняем функцию и кэшируем результат
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

def invalidate_cache(pattern: str) -> None:
    """Инвалидировать кэш по паттерну"""
    keys_to_delete = [key for key in cache.cache.keys() if pattern in key]
    for key in keys_to_delete:
        cache.delete(key)

# Специализированные функции кэширования
def cache_user_data(user_id: int, data: dict, ttl: int = 600) -> None:
    """Кэшировать данные пользователя"""
    cache.set(f"user:{user_id}", data, ttl)

def get_cached_user_data(user_id: int) -> Optional[dict]:
    """Получить кэшированные данные пользователя"""
    return cache.get(f"user:{user_id}")

def cache_guild_data(guild_id: int, data: dict, ttl: int = 600) -> None:
    """Кэшировать данные гильдии"""
    cache.set(f"guild:{guild_id}", data, ttl)

def get_cached_guild_data(guild_id: int) -> Optional[dict]:
    """Получить кэшированные данные гильдии"""
    return cache.get(f"guild:{guild_id}")

def cache_channel_messages(channel_id: int, page: int, data: dict, ttl: int = 60) -> None:
    """Кэшировать сообщения канала"""
    cache.set(f"messages:{channel_id}:{page}", data, ttl)

def get_cached_channel_messages(channel_id: int, page: int) -> Optional[dict]:
    """Получить кэшированные сообщения канала"""
    return cache.get(f"messages:{channel_id}:{page}")

def invalidate_user_cache(user_id: int) -> None:
    """Инвалидировать кэш пользователя"""
    invalidate_cache(f"user:{user_id}")

def invalidate_guild_cache(guild_id: int) -> None:
    """Инвалидировать кэш гильдии"""
    invalidate_cache(f"guild:{guild_id}")

def invalidate_channel_cache(channel_id: int) -> None:
    """Инвалидировать кэш канала"""
    invalidate_cache(f"messages:{channel_id}")

# Периодическая очистка кэша
def start_cache_cleanup():
    """Запустить периодическую очистку кэша"""
    import threading
    import time
    
    def cleanup_loop():
        while True:
            time.sleep(300)  # Очистка каждые 5 минут
            cache.cleanup_expired()
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()



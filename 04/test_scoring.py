"""
Модульные тесты для scoring.py и store.py.

Использует pytest с декоратором @cases для параметризации тестовых векторов.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import redis

from scoring import get_score, get_interests
from store import Store
from conftest import cases


class MockStore:
    """Простой мок-хранилище для unit-тестов."""
    
    def __init__(self):
        self._data = {}
    
    def cache_get(self, key):
        return self._data.get(key)
    
    def cache_set(self, key, value, ttl=0):
        self._data[key] = str(value)
    
    def get(self, key):
        return self._data.get(key)
    
    def set(self, key, value, ttl=0):
        self._data[key] = str(value)


class TestGetScore:
    """Тесты для функции get_score."""
    
    def test_score_with_all_parameters(self):
        """Проверка расчёта скоринга со всеми параметрами."""
        store = MockStore()
        result = get_score(
            store,
            phone="+79991234567",
            email="test@example.com",
            birthday=datetime(1990, 1, 1),
            gender=1,
            first_name="Иван",
            last_name="Иванов"
        )
        # phone: 1.5 + email: 1.5 + birthday+gender: 1.5 + name: 0.5 = 5.0
        assert result == 5.0
    
    def test_score_with_no_parameters(self):
        """Проверка расчёта скоринга без параметров."""
        store = MockStore()
        result = get_score(store)
        assert result == 0.0
    
    @cases([
        {"phone": "+79991234567", "email": None, "birthday": None, "gender": None, 
         "first_name": None, "last_name": None, "expected": 1.5},
        {"phone": None, "email": "test@example.com", "birthday": None, "gender": None,
         "first_name": None, "last_name": None, "expected": 1.5},
        {"phone": None, "email": None, "birthday": datetime(1990, 1, 1), "gender": 1,
         "first_name": None, "last_name": None, "expected": 1.5},
        {"phone": None, "email": None, "birthday": None, "gender": None,
         "first_name": "Иван", "last_name": "Иванов", "expected": 0.5},
        {"phone": "+79991234567", "email": "test@example.com", "birthday": None, "gender": None,
         "first_name": None, "last_name": None, "expected": 3.0},
    ])
    def test_score_various_combinations(self, phone, email, birthday, gender, first_name, last_name, expected):
        """Проверка различных комбинаций параметров."""
        store = MockStore()
        result = get_score(store, phone=phone, email=email, birthday=birthday, 
                          gender=gender, first_name=first_name, last_name=last_name)
        assert result == expected
    
    def test_score_caching(self):
        """Проверка кэширования результата."""
        store = MockStore()
        
        # Первый вызов - рассчитывает и кэширует
        result1 = get_score(store, phone="+79991234567")
        assert result1 == 1.5
        
        # Второй вызов - должен взять из кэша
        result2 = get_score(store, phone="+79991234567")
        assert result2 == 1.5
    
    def test_score_with_empty_string_parameters(self):
        """Проверка с пустыми строками."""
        store = MockStore()
        result = get_score(store, phone="", email="", first_name="", last_name="")
        # Пустые строки считаются как False в Python
        assert result == 0.0


class TestGetInterests:
    """Тесты для функции get_interests."""
    
    def test_get_interests_with_data(self):
        """Проверка получения интересов из хранилища."""
        store = MockStore()
        interests = ["sport", "music", "travel"]
        store.set("i:test_cid", json.dumps(interests))
        
        result = get_interests(store, "test_cid")
        assert result == interests
    
    def test_get_interests_empty(self):
        """Проверка при отсутствии данных."""
        store = MockStore()
        result = get_interests(store, "nonexistent")
        assert result == []
    
    def test_get_interests_nonexistent_key(self):
        """Проверка при несуществующем ключе."""
        store = MockStore()
        result = get_interests(store, "no_such_cid")
        assert result == []


class TestStore:
    """Тесты для класса Store."""
    
    @patch('store.redis.Redis')
    def test_store_initialization(self, mock_redis):
        """Проверка инициализации Store."""
        store = Store(host="localhost", port=6379, retry_times=3)
        assert store.host == "localhost"
        assert store.port == 6379
        assert store.retry_times == 3
    
    @patch('store.redis.Redis')
    def test_cache_get_returns_none_on_error(self, mock_redis):
        """Проверка что cache_get возвращает None при ошибке соединения."""
        mock_instance = mock_redis.return_value
        mock_instance.get.side_effect = redis.ConnectionError("Connection error")
        
        store = Store(retry_times=1)
        # При ошибке cache_get должен вернуть None
        result = store.cache_get("test_key")
        assert result is None
    
    @patch('store.redis.Redis')
    def test_cache_set_silently_fails_on_error(self, mock_redis):
        """Проверка что cache_set молча проваливается при ошибке."""
        mock_instance = mock_redis.return_value
        mock_instance.setex.side_effect = redis.ConnectionError("Connection error")
        
        store = Store(retry_times=1)
        # cache_set не должен поднимать исключение
        store.cache_set("test_key", "test_value", ttl=60)


class TestStoreWithMockRedis:
    """Тесты Store с мокированным Redis."""
    
    @patch('store.redis.Redis')
    def test_get_with_successful_response(self, mock_redis):
        """Проверка get при успешном ответе."""
        mock_instance = mock_redis.return_value
        mock_instance.get.return_value = '["sport", "music"]'
        
        store = Store()
        result = store.get("i:test_cid")
        assert result == '["sport", "music"]'
    
    @patch('store.redis.Redis')
    def test_set_with_ttl(self, mock_redis):
        """Проверка set с TTL."""
        mock_instance = mock_redis.return_value
        
        store = Store()
        store.set("test_key", "test_value", ttl=300)
        mock_instance.setex.assert_called_once_with("test_key", 300, "test_value")
    
    @patch('store.redis.Redis')
    def test_set_without_ttl(self, mock_redis):
        """Проверка set без TTL."""
        mock_instance = mock_redis.return_value
        
        store = Store()
        store.set("test_key", "test_value")
        mock_instance.set.assert_called_once_with("test_key", "test_value")
    
    @patch('store.redis.Redis')
    def test_cache_get_with_successful_response(self, mock_redis):
        """Проверка cache_get при успешном ответе."""
        mock_instance = mock_redis.return_value
        mock_instance.get.return_value = "4.5"
        
        store = Store()
        result = store.cache_get("score_key")
        assert result == "4.5"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

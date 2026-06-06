"""
Декоратор @cases для параметризации тестовыми векторами.
"""

import functools
import pytest


def cases(test_vectors):
    """
    Декоратор, который параметризует тестовый метод разными тест-векторами.
    Использует pytest.param для передачи каждого вектора как отдельного кейса.
    
    Пример использования:
        @cases([
            {"account": "horns&hoofs", "login": "h&f", "expected": 401},
            {"account": "horns&hoofs", "login": "admin", "expected": 200},
        ])
        def test_auth(self, account, login, expected):
            assert response == expected
    """
    def decorator(func):
        if not test_vectors:
            return func
            
        # Получаем имена параметров из ключей первого вектора
        param_names = list(test_vectors[0].keys())
        
        # Подготавливаем параметры и ID для pytest
        params = []
        ids = []
        for vector in test_vectors:
            # Создаем кортеж значений в том же порядке, что и param_names
            param_values = tuple(vector[key] for key in param_names)
            params.append(param_values)
            
            # Формируем уникальный ID для отображения в выводе pytest
            id_parts = []
            for key in param_names:
                value = vector[key]
                id_parts.append(f"{key}={value}")
            ids.append(" | ".join(id_parts))
        
        # Применяем pytest.mark.parametrize
        param_names_str = ",".join(param_names)
        wrapped = pytest.mark.parametrize(param_names_str, params, ids=ids)(func)
        return wrapped
    return decorator

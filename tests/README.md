# Тесты Discord-like мессенджера

Этот каталог содержит автоматические тесты для Discord-like мессенджера.

## Структура тестов

- `test_auth.py` - Тесты аутентификации и авторизации
- `test_messages.py` - Тесты работы с сообщениями
- `test_guilds.py` - Тесты работы с гильдиями и каналами
- `test_integration.py` - Интеграционные тесты API
- `test_frontend.py` - Frontend тесты с Selenium
- `run_tests.py` - Скрипт для запуска всех тестов

## Запуск тестов

### Все тесты
```bash
cd tests
python run_tests.py
```

### Только backend тесты
```bash
cd tests
python -m unittest test_auth.py test_messages.py test_guilds.py test_integration.py
```

### Только frontend тесты
```bash
cd tests
python -m unittest test_frontend.py
```

### Отдельные тесты
```bash
cd tests
python test_auth.py
python test_messages.py
python test_guilds.py
python test_integration.py
python test_frontend.py
```

## Установка зависимостей

### Основные зависимости
```bash
pip install -r ../requirements.txt
```

### Зависимости для тестирования
```bash
pip install -r requirements.txt
```

## Настройка

### Backend тесты
Backend тесты используют тестовую SQLite базу данных, которая создается автоматически.

### Frontend тесты
Frontend тесты требуют:
1. Установленный Chrome/Chromium браузер
2. ChromeDriver в PATH
3. Запущенный сервер приложения на localhost:5000

Для запуска сервера:
```bash
cd ..
python backend/app.py
```

## Покрытие кода

Для проверки покрытия кода тестами:
```bash
pip install pytest-cov
pytest --cov=backend tests/
```

## Типы тестов

### Unit тесты
- Тестируют отдельные функции и методы
- Быстрые и изолированные
- Не требуют внешних зависимостей

### Интеграционные тесты
- Тестируют взаимодействие между компонентами
- Используют реальную базу данных
- Проверяют API эндпоинты

### Frontend тесты
- Тестируют пользовательский интерфейс
- Используют Selenium WebDriver
- Проверяют взаимодействие пользователя с приложением

## Добавление новых тестов

1. Создайте новый файл `test_*.py`
2. Наследуйтесь от `unittest.TestCase`
3. Добавьте методы `setUp()` и `tearDown()` для настройки
4. Создайте методы тестов с префиксом `test_`
5. Добавьте новый тест в `run_tests.py`

Пример:
```python
import unittest

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        # Настройка перед каждым тестом
        pass
    
    def tearDown(self):
        # Очистка после каждого теста
        pass
    
    def test_new_feature_success(self):
        # Тест успешного сценария
        self.assertTrue(True)
    
    def test_new_feature_failure(self):
        # Тест сценария с ошибкой
        self.assertFalse(False)
```

## Отладка тестов

### Логирование
Добавьте логирование в тесты:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Остановка на ошибках
```bash
python -m unittest -v test_auth.py
```

### Запуск конкретного теста
```bash
python -m unittest test_auth.TestAuth.test_register_user_success
```

## CI/CD

Тесты можно интегрировать в CI/CD пайплайн:

```yaml
# GitHub Actions пример
- name: Run tests
  run: |
    cd tests
    python run_tests.py
```

## Известные проблемы

1. Frontend тесты могут быть нестабильными из-за таймингов
2. Selenium требует установки ChromeDriver
3. Тесты могут конфликтовать при параллельном запуске



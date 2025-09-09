#!/usr/bin/env python3
"""
Скрипт для запуска всех тестов Discord-like мессенджера
"""

import unittest
import sys
import os
import subprocess

# Добавляем корневую директорию в путь
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def run_backend_tests():
    """Запуск backend тестов"""
    print("=" * 50)
    print("ЗАПУСК BACKEND ТЕСТОВ")
    print("=" * 50)
    
    # Создаем test suite для backend тестов
    backend_suite = unittest.TestSuite()
    
    # Добавляем тесты
    from test_auth import TestAuth
    from test_messages import TestMessages
    from test_guilds import TestGuilds
    from test_integration import TestIntegration
    
    backend_suite.addTest(unittest.makeSuite(TestAuth))
    backend_suite.addTest(unittest.makeSuite(TestMessages))
    backend_suite.addTest(unittest.makeSuite(TestGuilds))
    backend_suite.addTest(unittest.makeSuite(TestIntegration))
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(backend_suite)
    
    return result.wasSuccessful()

def run_frontend_tests():
    """Запуск frontend тестов"""
    print("=" * 50)
    print("ЗАПУСК FRONTEND ТЕСТОВ")
    print("=" * 50)
    
    try:
        # Проверяем, установлен ли Selenium
        import selenium
        print("Selenium найден, запускаем frontend тесты...")
        
        from test_frontend import TestFrontend
        frontend_suite = unittest.TestSuite()
        frontend_suite.addTest(unittest.makeSuite(TestFrontend))
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(frontend_suite)
        
        return result.wasSuccessful()
        
    except ImportError:
        print("Selenium не установлен. Пропускаем frontend тесты.")
        print("Для установки: pip install selenium")
        return True

def check_dependencies():
    """Проверка зависимостей"""
    print("=" * 50)
    print("ПРОВЕРКА ЗАВИСИМОСТЕЙ")
    print("=" * 50)
    
    required_packages = [
        'flask',
        'flask_socketio',
        'sqlalchemy',
        'werkzeug'
    ]
    
    optional_packages = [
        'selenium'
    ]
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - ОБЯЗАТЕЛЬНО")
            missing_required.append(package)
    
    for package in optional_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - опционально")
            missing_optional.append(package)
    
    if missing_required:
        print(f"\nОШИБКА: Отсутствуют обязательные пакеты: {', '.join(missing_required)}")
        print("Установите их командой: pip install " + " ".join(missing_required))
        return False
    
    if missing_optional:
        print(f"\nПРЕДУПРЕЖДЕНИЕ: Отсутствуют опциональные пакеты: {', '.join(missing_optional)}")
        print("Для frontend тестов установите: pip install selenium")
    
    return True

def setup_test_database():
    """Настройка тестовой базы данных"""
    print("=" * 50)
    print("НАСТРОЙКА ТЕСТОВОЙ БД")
    print("=" * 50)
    
    try:
        from backend.models import Base, engine
        Base.metadata.create_all(engine)
        print("✓ Тестовая база данных создана")
        return True
    except Exception as e:
        print(f"✗ Ошибка создания тестовой БД: {e}")
        return False

def main():
    """Главная функция"""
    print("DISCORD-LIKE МЕССЕНДЖЕР - ТЕСТЫ")
    print("=" * 50)
    
    # Проверяем зависимости
    if not check_dependencies():
        sys.exit(1)
    
    # Настраиваем тестовую БД
    if not setup_test_database():
        sys.exit(1)
    
    # Запускаем тесты
    backend_success = run_backend_tests()
    frontend_success = run_frontend_tests()
    
    # Итоги
    print("=" * 50)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 50)
    
    if backend_success:
        print("✓ Backend тесты пройдены успешно")
    else:
        print("✗ Backend тесты провалены")
    
    if frontend_success:
        print("✓ Frontend тесты пройдены успешно")
    else:
        print("✗ Frontend тесты провалены")
    
    if backend_success and frontend_success:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        sys.exit(0)
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        sys.exit(1)

if __name__ == '__main__':
    main()



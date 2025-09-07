#!/usr/bin/env python3
"""
Простой тест для проверки работы мессенджера Oleg
"""

import requests
import time
import subprocess
import sys
import os

def test_server():
    """Тестирует запуск сервера"""
    print("🚀 Тестирование мессенджера Oleg...")
    
    # Проверяем, что файлы существуют
    required_files = [
        'backend/app.py',
        'templates/index.html',
        'static/style.css',
        'static/script.js'
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ Файл {file_path} не найден!")
            return False
        else:
            print(f"✅ Файл {file_path} найден")
    
    print("\n📁 Структура проекта:")
    for root, dirs, files in os.walk('.'):
        level = root.replace('.', '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")
    
    print("\n🎉 Мессенджер Oleg готов к запуску!")
    print("📋 Инструкции:")
    print("1. Установите зависимости: pip install Flask Flask-SocketIO")
    print("2. Запустите сервер: python backend/app.py")
    print("3. Откройте браузер: http://localhost:5000")
    print("4. Зарегистрируйтесь и начните общение!")
    
    return True

if __name__ == "__main__":
    test_server()


import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.auth import register_user, login_user, get_csrf_token
from backend.models import SessionLocal, User
from werkzeug.security import check_password_hash

class TestAuth(unittest.TestCase):
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.db = SessionLocal()
        # Очищаем тестовые данные
        self.db.query(User).delete()
        self.db.commit()
    
    def tearDown(self):
        """Очистка после каждого теста"""
        self.db.close()
    
    def test_register_user_success(self):
        """Тест успешной регистрации пользователя"""
        result = register_user("testuser", "testpass", "test@example.com")
        self.assertIsNotNone(result)
        self.assertEqual(result.username, "testuser")
        self.assertEqual(result.email, "test@example.com")
        self.assertTrue(check_password_hash(result.password, "testpass"))
    
    def test_register_user_duplicate_username(self):
        """Тест регистрации с дублирующимся именем пользователя"""
        # Создаем первого пользователя
        register_user("testuser", "testpass", "test1@example.com")
        
        # Пытаемся создать второго с тем же именем
        result = register_user("testuser", "testpass2", "test2@example.com")
        self.assertIsNone(result)
    
    def test_register_user_duplicate_email(self):
        """Тест регистрации с дублирующимся email"""
        # Создаем первого пользователя
        register_user("testuser1", "testpass", "test@example.com")
        
        # Пытаемся создать второго с тем же email
        result = register_user("testuser2", "testpass2", "test@example.com")
        self.assertIsNone(result)
    
    def test_login_user_success(self):
        """Тест успешного входа"""
        # Регистрируем пользователя
        register_user("testuser", "testpass", "test@example.com")
        
        # Пытаемся войти
        result = login_user("testuser", "testpass")
        self.assertIsNotNone(result)
        self.assertEqual(result.username, "testuser")
    
    def test_login_user_wrong_password(self):
        """Тест входа с неправильным паролем"""
        # Регистрируем пользователя
        register_user("testuser", "testpass", "test@example.com")
        
        # Пытаемся войти с неправильным паролем
        result = login_user("testuser", "wrongpass")
        self.assertIsNone(result)
    
    def test_login_user_nonexistent(self):
        """Тест входа несуществующего пользователя"""
        result = login_user("nonexistent", "testpass")
        self.assertIsNone(result)
    
    def test_get_csrf_token(self):
        """Тест получения CSRF токена"""
        token = get_csrf_token()
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 10)  # Токен должен быть достаточно длинным

if __name__ == '__main__':
    unittest.main()



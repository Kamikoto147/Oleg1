import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.messages import create_message, get_messages, get_messages_count, edit_message, delete_message
from backend.models import SessionLocal, User, Channel, Guild
from datetime import datetime

class TestMessages(unittest.TestCase):
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.db = SessionLocal()
        # Очищаем тестовые данные
        self.db.query(User).delete()
        self.db.query(Channel).delete()
        self.db.query(Guild).delete()
        self.db.commit()
        
        # Создаем тестового пользователя
        self.test_user = User(username="testuser", password="hashedpass", email="test@example.com")
        self.db.add(self.test_user)
        
        # Создаем тестовую гильдию
        self.test_guild = Guild(name="Test Guild", owner_id=self.test_user.id)
        self.db.add(self.test_guild)
        
        # Создаем тестовый канал
        self.test_channel = Channel(name="test-channel", guild_id=self.test_guild.id)
        self.db.add(self.test_channel)
        
        self.db.commit()
    
    def tearDown(self):
        """Очистка после каждого теста"""
        self.db.close()
    
    def test_create_message_success(self):
        """Тест успешного создания сообщения"""
        message = create_message(self.test_channel.id, "testuser", "Hello, world!")
        self.assertIsNotNone(message)
        self.assertEqual(message.content, "Hello, world!")
        self.assertEqual(message.user.username, "testuser")
        self.assertEqual(message.channel_id, self.test_channel.id)
    
    def test_create_message_nonexistent_user(self):
        """Тест создания сообщения несуществующим пользователем"""
        message = create_message(self.test_channel.id, "nonexistent", "Hello!")
        self.assertIsNone(message)
    
    def test_create_message_nonexistent_channel(self):
        """Тест создания сообщения в несуществующем канале"""
        message = create_message(99999, "testuser", "Hello!")
        self.assertIsNone(message)
    
    def test_get_messages(self):
        """Тест получения сообщений"""
        # Создаем несколько сообщений
        create_message(self.test_channel.id, "testuser", "Message 1")
        create_message(self.test_channel.id, "testuser", "Message 2")
        create_message(self.test_channel.id, "testuser", "Message 3")
        
        messages = get_messages(self.test_channel.id)
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0].content, "Message 1")
        self.assertEqual(messages[2].content, "Message 3")
    
    def test_get_messages_with_pagination(self):
        """Тест получения сообщений с пагинацией"""
        # Создаем 10 сообщений
        for i in range(10):
            create_message(self.test_channel.id, "testuser", f"Message {i+1}")
        
        # Получаем первые 5 сообщений
        messages = get_messages(self.test_channel.id, limit=5, offset=0)
        self.assertEqual(len(messages), 5)
        
        # Получаем следующие 5 сообщений
        messages = get_messages(self.test_channel.id, limit=5, offset=5)
        self.assertEqual(len(messages), 5)
    
    def test_get_messages_count(self):
        """Тест подсчета сообщений"""
        # Создаем 5 сообщений
        for i in range(5):
            create_message(self.test_channel.id, "testuser", f"Message {i+1}")
        
        count = get_messages_count(self.test_channel.id)
        self.assertEqual(count, 5)
    
    def test_edit_message_success(self):
        """Тест успешного редактирования сообщения"""
        # Создаем сообщение
        message = create_message(self.test_channel.id, "testuser", "Original message")
        self.assertIsNotNone(message)
        
        # Редактируем сообщение
        result = edit_message(self.test_channel.id, message.id, "Edited message")
        self.assertTrue(result)
        
        # Проверяем, что сообщение изменилось
        messages = get_messages(self.test_channel.id)
        self.assertEqual(messages[0].content, "Edited message")
    
    def test_edit_message_nonexistent(self):
        """Тест редактирования несуществующего сообщения"""
        result = edit_message(self.test_channel.id, 99999, "New content")
        self.assertFalse(result)
    
    def test_delete_message_success(self):
        """Тест успешного удаления сообщения"""
        # Создаем сообщение
        message = create_message(self.test_channel.id, "testuser", "Message to delete")
        self.assertIsNotNone(message)
        
        # Удаляем сообщение
        result = delete_message(self.test_channel.id, message.id)
        self.assertTrue(result)
        
        # Проверяем, что сообщение удалено
        messages = get_messages(self.test_channel.id)
        self.assertEqual(len(messages), 0)
    
    def test_delete_message_nonexistent(self):
        """Тест удаления несуществующего сообщения"""
        result = delete_message(self.test_channel.id, 99999)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()



import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.guilds import create_guild, get_guild, delete_guild, list_guilds, create_channel, get_channel, list_channels
from backend.models import SessionLocal, User, Guild, Channel

class TestGuilds(unittest.TestCase):
    
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
        self.db.commit()
    
    def tearDown(self):
        """Очистка после каждого теста"""
        self.db.close()
    
    def test_create_guild_success(self):
        """Тест успешного создания гильдии"""
        guild = create_guild("Test Guild", self.test_user.id)
        self.assertIsNotNone(guild)
        self.assertEqual(guild.name, "Test Guild")
        self.assertEqual(guild.owner_id, self.test_user.id)
    
    def test_create_guild_nonexistent_user(self):
        """Тест создания гильдии несуществующим пользователем"""
        guild = create_guild("Test Guild", 99999)
        self.assertIsNone(guild)
    
    def test_get_guild_success(self):
        """Тест получения гильдии"""
        guild = create_guild("Test Guild", self.test_user.id)
        self.assertIsNotNone(guild)
        
        retrieved_guild = get_guild(guild.id)
        self.assertIsNotNone(retrieved_guild)
        self.assertEqual(retrieved_guild.name, "Test Guild")
    
    def test_get_guild_nonexistent(self):
        """Тест получения несуществующей гильдии"""
        guild = get_guild(99999)
        self.assertIsNone(guild)
    
    def test_delete_guild_success(self):
        """Тест успешного удаления гильдии"""
        guild = create_guild("Test Guild", self.test_user.id)
        self.assertIsNotNone(guild)
        
        result = delete_guild(guild.id, self.test_user.id)
        self.assertTrue(result)
        
        # Проверяем, что гильдия удалена
        deleted_guild = get_guild(guild.id)
        self.assertIsNone(deleted_guild)
    
    def test_delete_guild_not_owner(self):
        """Тест удаления гильдии не владельцем"""
        guild = create_guild("Test Guild", self.test_user.id)
        self.assertIsNotNone(guild)
        
        # Пытаемся удалить гильдию другим пользователем
        result = delete_guild(guild.id, 99999)
        self.assertFalse(result)
    
    def test_list_guilds(self):
        """Тест получения списка гильдий пользователя"""
        # Создаем несколько гильдий
        guild1 = create_guild("Guild 1", self.test_user.id)
        guild2 = create_guild("Guild 2", self.test_user.id)
        
        guilds = list_guilds(self.test_user.id)
        self.assertEqual(len(guilds), 2)
        guild_names = [g.name for g in guilds]
        self.assertIn("Guild 1", guild_names)
        self.assertIn("Guild 2", guild_names)
    
    def test_create_channel_success(self):
        """Тест успешного создания канала"""
        guild = create_guild("Test Guild", self.test_user.id)
        self.assertIsNotNone(guild)
        
        channel = create_channel("test-channel", guild.id)
        self.assertIsNotNone(channel)
        self.assertEqual(channel.name, "test-channel")
        self.assertEqual(channel.guild_id, guild.id)
    
    def test_create_channel_nonexistent_guild(self):
        """Тест создания канала в несуществующей гильдии"""
        channel = create_channel("test-channel", 99999)
        self.assertIsNone(channel)
    
    def test_get_channel_success(self):
        """Тест получения канала"""
        guild = create_guild("Test Guild", self.test_user.id)
        channel = create_channel("test-channel", guild.id)
        
        retrieved_channel = get_channel(channel.id)
        self.assertIsNotNone(retrieved_channel)
        self.assertEqual(retrieved_channel.name, "test-channel")
    
    def test_list_channels(self):
        """Тест получения списка каналов гильдии"""
        guild = create_guild("Test Guild", self.test_user.id)
        
        # Создаем несколько каналов
        channel1 = create_channel("channel-1", guild.id)
        channel2 = create_channel("channel-2", guild.id)
        
        channels = list_channels(guild.id)
        self.assertEqual(len(channels), 2)
        channel_names = [c.name for c in channels]
        self.assertIn("channel-1", channel_names)
        self.assertIn("channel-2", channel_names)

if __name__ == '__main__':
    unittest.main()



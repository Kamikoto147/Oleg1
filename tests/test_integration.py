import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.app import app
from backend.models import SessionLocal, User, Guild, Channel
import json

class TestIntegration(unittest.TestCase):
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.app = app.test_client()
        self.app.testing = True
        
        self.db = SessionLocal()
        # Очищаем тестовые данные
        self.db.query(User).delete()
        self.db.query(Channel).delete()
        self.db.query(Guild).delete()
        self.db.commit()
    
    def tearDown(self):
        """Очистка после каждого теста"""
        self.db.close()
    
    def test_register_and_login_flow(self):
        """Тест полного цикла регистрации и входа"""
        # Регистрация
        response = self.app.post('/api/register', 
                               data=json.dumps({
                                   'username': 'testuser',
                                   'password': 'testpass',
                                   'email': 'test@example.com'
                               }),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['username'], 'testuser')
        
        # Вход
        response = self.app.post('/api/login',
                               data=json.dumps({
                                   'username': 'testuser',
                                   'password': 'testpass'
                               }),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['username'], 'testuser')
    
    def test_guild_creation_flow(self):
        """Тест создания гильдии через API"""
        # Сначала регистрируемся и входим
        self.app.post('/api/register', 
                     data=json.dumps({
                         'username': 'testuser',
                         'password': 'testpass',
                         'email': 'test@example.com'
                     }),
                     content_type='application/json')
        
        login_response = self.app.post('/api/login',
                                     data=json.dumps({
                                         'username': 'testuser',
                                         'password': 'testpass'
                                     }),
                                     content_type='application/json')
        
        # Создаем гильдию
        response = self.app.post('/api/guilds',
                               data=json.dumps({
                                   'name': 'Test Guild'
                               }),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['name'], 'Test Guild')
    
    def test_message_flow(self):
        """Тест отправки сообщений через API"""
        # Регистрируемся и входим
        self.app.post('/api/register', 
                     data=json.dumps({
                         'username': 'testuser',
                         'password': 'testpass',
                         'email': 'test@example.com'
                     }),
                     content_type='application/json')
        
        self.app.post('/api/login',
                     data=json.dumps({
                         'username': 'testuser',
                         'password': 'testpass'
                     }),
                     content_type='application/json')
        
        # Создаем гильдию
        guild_response = self.app.post('/api/guilds',
                                     data=json.dumps({
                                         'name': 'Test Guild'
                                     }),
                                     content_type='application/json')
        
        guild_data = json.loads(guild_response.data)
        guild_id = guild_data['id']
        
        # Создаем канал
        channel_response = self.app.post(f'/api/guilds/{guild_id}/channels',
                                       data=json.dumps({
                                           'name': 'test-channel'
                                       }),
                                       content_type='application/json')
        
        channel_data = json.loads(channel_response.data)
        channel_id = channel_data['id']
        
        # Отправляем сообщение
        response = self.app.post(f'/api/channels/{channel_id}/messages',
                               data=json.dumps({
                                   'content': 'Hello, world!'
                               }),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['content'], 'Hello, world!')
    
    def test_search_users(self):
        """Тест поиска пользователей"""
        # Создаем несколько пользователей
        users = ['alice', 'bob', 'charlie', 'alex']
        for username in users:
            self.app.post('/api/register', 
                         data=json.dumps({
                             'username': username,
                             'password': 'testpass',
                             'email': f'{username}@example.com'
                         }),
                         content_type='application/json')
        
        # Входим как alice
        self.app.post('/api/login',
                     data=json.dumps({
                         'username': 'alice',
                         'password': 'testpass'
                     }),
                     content_type='application/json')
        
        # Ищем пользователей
        response = self.app.get('/api/search/users?q=al')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        results = data['results']
        
        # Должны найти alice и alex
        usernames = [r['username'] for r in results]
        self.assertIn('alice', usernames)
        self.assertIn('alex', usernames)
        self.assertNotIn('bob', usernames)
        self.assertNotIn('charlie', usernames)
    
    def test_poll_creation_and_voting(self):
        """Тест создания опроса и голосования"""
        # Регистрируемся и входим
        self.app.post('/api/register', 
                     data=json.dumps({
                         'username': 'testuser',
                         'password': 'testpass',
                         'email': 'test@example.com'
                     }),
                     content_type='application/json')
        
        self.app.post('/api/login',
                     data=json.dumps({
                         'username': 'testuser',
                         'password': 'testpass'
                     }),
                     content_type='application/json')
        
        # Создаем гильдию и канал
        guild_response = self.app.post('/api/guilds',
                                     data=json.dumps({
                                         'name': 'Test Guild'
                                     }),
                                     content_type='application/json')
        
        guild_data = json.loads(guild_response.data)
        guild_id = guild_data['id']
        
        channel_response = self.app.post(f'/api/guilds/{guild_id}/channels',
                                       data=json.dumps({
                                           'name': 'test-channel'
                                       }),
                                       content_type='application/json')
        
        channel_data = json.loads(channel_response.data)
        channel_id = channel_data['id']
        
        # Отправляем сообщение
        message_response = self.app.post(f'/api/channels/{channel_id}/messages',
                                       data=json.dumps({
                                           'content': 'Test message'
                                       }),
                                       content_type='application/json')
        
        message_data = json.loads(message_response.data)
        message_id = message_data['id']
        
        # Создаем опрос
        poll_response = self.app.post(f'/api/messages/{message_id}/poll',
                                    data=json.dumps({
                                        'question': 'What is your favorite color?',
                                        'options': ['Red', 'Blue', 'Green'],
                                        'allow_multiple': False
                                    }),
                                    content_type='application/json')
        
        self.assertEqual(poll_response.status_code, 201)
        poll_data = json.loads(poll_response.data)
        self.assertEqual(poll_data['question'], 'What is your favorite color?')
        self.assertEqual(len(poll_data['options']), 3)
        
        # Голосуем в опросе
        vote_response = self.app.post(f'/api/polls/{poll_data["id"]}/vote',
                                    data=json.dumps({
                                        'option_id': '1'
                                    }),
                                    content_type='application/json')
        
        self.assertEqual(vote_response.status_code, 200)
        vote_data = json.loads(vote_response.data)
        
        # Проверяем, что голос засчитан
        option_1 = next(opt for opt in vote_data['options'] if opt['id'] == '1')
        self.assertEqual(option_1['votes'], 1)

if __name__ == '__main__':
    unittest.main()



import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

class TestFrontend(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Настройка браузера для всех тестов"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Запуск без GUI
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.wait = WebDriverWait(cls.driver, 10)
    
    @classmethod
    def tearDownClass(cls):
        """Закрытие браузера после всех тестов"""
        cls.driver.quit()
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.driver.get('http://localhost:5000')
        time.sleep(1)  # Даем время на загрузку
    
    def test_login_form_exists(self):
        """Тест наличия формы входа"""
        username_input = self.driver.find_element(By.ID, 'username')
        password_input = self.driver.find_element(By.ID, 'password')
        login_button = self.driver.find_element(By.ID, 'login-btn')
        
        self.assertIsNotNone(username_input)
        self.assertIsNotNone(password_input)
        self.assertIsNotNone(login_button)
    
    def test_register_form_exists(self):
        """Тест наличия формы регистрации"""
        # Переключаемся на вкладку регистрации
        register_tab = self.driver.find_element(By.ID, 'register-tab')
        register_tab.click()
        
        username_input = self.driver.find_element(By.ID, 'reg-username')
        password_input = self.driver.find_element(By.ID, 'reg-password')
        email_input = self.driver.find_element(By.ID, 'reg-email')
        register_button = self.driver.find_element(By.ID, 'register-btn')
        
        self.assertIsNotNone(username_input)
        self.assertIsNotNone(password_input)
        self.assertIsNotNone(email_input)
        self.assertIsNotNone(register_button)
    
    def test_message_input_exists_after_login(self):
        """Тест наличия поля ввода сообщений после входа"""
        # Регистрируемся
        register_tab = self.driver.find_element(By.ID, 'register-tab')
        register_tab.click()
        
        username_input = self.driver.find_element(By.ID, 'reg-username')
        password_input = self.driver.find_element(By.ID, 'reg-password')
        email_input = self.driver.find_element(By.ID, 'reg-email')
        register_button = self.driver.find_element(By.ID, 'register-btn')
        
        username_input.send_keys('testuser')
        password_input.send_keys('testpass')
        email_input.send_keys('test@example.com')
        register_button.click()
        
        time.sleep(2)  # Ждем регистрации
        
        # Проверяем, что появилось поле ввода сообщений
        try:
            message_input = self.wait.until(
                EC.presence_of_element_located((By.ID, 'message-input'))
            )
            self.assertIsNotNone(message_input)
        except:
            self.fail("Поле ввода сообщений не найдено после входа")
    
    def test_guild_creation_ui(self):
        """Тест UI создания гильдии"""
        # Входим в систему
        self.login_user('testuser', 'testpass')
        
        # Ищем кнопку создания гильдии
        try:
            create_guild_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, 'create-guild-btn'))
            )
            create_guild_btn.click()
            
            # Проверяем, что появилось модальное окно
            modal = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, 'modal'))
            )
            self.assertIsNotNone(modal)
            
        except:
            self.fail("UI создания гильдии не найден")
    
    def test_channel_switching(self):
        """Тест переключения между каналами"""
        # Входим в систему
        self.login_user('testuser', 'testpass')
        
        # Создаем гильдию
        self.create_test_guild()
        
        # Ищем каналы
        try:
            channels = self.wait.until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'channel-item'))
            )
            
            if len(channels) > 0:
                # Кликаем на первый канал
                channels[0].click()
                time.sleep(1)
                
                # Проверяем, что канал активен
                active_channel = self.driver.find_element(By.CLASS_NAME, 'channel-item.active')
                self.assertIsNotNone(active_channel)
            
        except:
            self.fail("Переключение каналов не работает")
    
    def test_message_sending(self):
        """Тест отправки сообщений"""
        # Входим в систему
        self.login_user('testuser', 'testpass')
        
        # Создаем гильдию и переходим в канал
        self.create_test_guild()
        self.switch_to_channel()
        
        # Отправляем сообщение
        message_input = self.driver.find_element(By.ID, 'message-input')
        send_button = self.driver.find_element(By.ID, 'send-btn')
        
        message_input.send_keys('Test message')
        send_button.click()
        
        time.sleep(1)
        
        # Проверяем, что сообщение появилось
        try:
            messages = self.driver.find_elements(By.CLASS_NAME, 'message-item')
            self.assertGreater(len(messages), 0)
        except:
            self.fail("Сообщение не было отправлено")
    
    def test_emoji_picker(self):
        """Тест панели эмодзи"""
        # Входим в систему
        self.login_user('testuser', 'testpass')
        
        # Создаем гильдию и переходим в канал
        self.create_test_guild()
        self.switch_to_channel()
        
        # Кликаем на кнопку эмодзи
        emoji_btn = self.driver.find_element(By.ID, 'emoji-btn')
        emoji_btn.click()
        
        # Проверяем, что появилась панель эмодзи
        try:
            emoji_picker = self.wait.until(
                EC.presence_of_element_located((By.ID, 'emoji-picker'))
            )
            self.assertIsNotNone(emoji_picker)
        except:
            self.fail("Панель эмодзи не открылась")
    
    def test_sticker_panel(self):
        """Тест панели стикеров"""
        # Входим в систему
        self.login_user('testuser', 'testpass')
        
        # Создаем гильдию и переходим в канал
        self.create_test_guild()
        self.switch_to_channel()
        
        # Кликаем на кнопку стикеров
        sticker_btn = self.driver.find_element(By.ID, 'sticker-btn')
        sticker_btn.click()
        
        # Проверяем, что появилась панель стикеров
        try:
            sticker_panel = self.wait.until(
                EC.presence_of_element_located((By.ID, 'sticker-panel'))
            )
            self.assertIsNotNone(sticker_panel)
        except:
            self.fail("Панель стикеров не открылась")
    
    def test_poll_modal(self):
        """Тест модального окна создания опроса"""
        # Входим в систему
        self.login_user('testuser', 'testpass')
        
        # Создаем гильдию и переходим в канал
        self.create_test_guild()
        self.switch_to_channel()
        
        # Кликаем на кнопку создания опроса
        poll_btn = self.driver.find_element(By.ID, 'poll-btn')
        poll_btn.click()
        
        # Проверяем, что появилось модальное окно опроса
        try:
            poll_modal = self.wait.until(
                EC.presence_of_element_located((By.ID, 'poll-modal'))
            )
            self.assertIsNotNone(poll_modal)
            
            # Проверяем наличие полей формы
            question_input = self.driver.find_element(By.ID, 'poll-question')
            self.assertIsNotNone(question_input)
            
        except:
            self.fail("Модальное окно опроса не открылось")
    
    # Вспомогательные методы
    def login_user(self, username, password):
        """Вход пользователя в систему"""
        username_input = self.driver.find_element(By.ID, 'username')
        password_input = self.driver.find_element(By.ID, 'password')
        login_button = self.driver.find_element(By.ID, 'login-btn')
        
        username_input.send_keys(username)
        password_input.send_keys(password)
        login_button.click()
        
        time.sleep(2)
    
    def create_test_guild(self):
        """Создание тестовой гильдии"""
        create_guild_btn = self.driver.find_element(By.ID, 'create-guild-btn')
        create_guild_btn.click()
        
        guild_name_input = self.driver.find_element(By.ID, 'guild-name')
        create_button = self.driver.find_element(By.ID, 'create-guild-confirm')
        
        guild_name_input.send_keys('Test Guild')
        create_button.click()
        
        time.sleep(2)
    
    def switch_to_channel(self):
        """Переключение на первый доступный канал"""
        try:
            channels = self.wait.until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'channel-item'))
            )
            if len(channels) > 0:
                channels[0].click()
                time.sleep(1)
        except:
            pass

if __name__ == '__main__':
    unittest.main()



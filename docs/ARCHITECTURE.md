# Архитектура Discord-like мессенджера

Подробное описание архитектуры, компонентов и принципов проектирования.

## Содержание

- [Обзор архитектуры](#обзор-архитектуры)
- [Backend архитектура](#backend-архитектура)
- [Frontend архитектура](#frontend-архитектура)
- [База данных](#база-данных)
- [Real-time коммуникация](#real-time-коммуникация)
- [Безопасность](#безопасность)
- [Производительность](#производительность)
- [Масштабируемость](#масштабируемость)
- [Мониторинг и логирование](#мониторинг-и-логирование)

## Обзор архитектуры

### Принципы проектирования

1. **Модульность** - Разделение на независимые модули
2. **Масштабируемость** - Возможность горизонтального масштабирования
3. **Безопасность** - Многоуровневая защита
4. **Производительность** - Оптимизация на всех уровнях
5. **Тестируемость** - Полное покрытие тестами
6. **Maintainability** - Легкость поддержки и развития

### Общая схема

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   Mobile App    │    │   Desktop App   │
│   (Frontend)    │    │   (Future)      │    │   (Future)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      Load Balancer        │
                    │      (Nginx/HAProxy)      │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      Flask App            │
                    │   (Web Server + API)      │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │    Socket.IO Server       │
                    │   (Real-time Events)      │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      Database             │
                    │   (SQLite/PostgreSQL)     │
                    └───────────────────────────┘
```

## Backend архитектура

### Структура модулей

```
backend/
├── app.py                    # Основное Flask приложение
├── models.py                 # SQLAlchemy модели
├── auth.py                   # Аутентификация и авторизация
├── users.py                  # Управление пользователями
├── guilds.py                 # Управление гильдиями и каналами
├── messages.py               # Управление сообщениями
├── files.py                  # Загрузка и обработка файлов
├── utils.py                  # Утилиты и хелперы
├── cache.py                  # Система кэширования
├── emojis_stickers_polls.py  # Эмодзи, стикеры, опросы
└── init_permissions.py       # Инициализация прав
```

### Основные компоненты

#### Flask App (app.py)
- **Назначение**: Основное веб-приложение
- **Функции**:
  - Маршрутизация HTTP запросов
  - Обработка WebSocket соединений
  - Инициализация приложения
  - Конфигурация

```python
# Основная структура
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# API маршруты
@app.route('/api/register', methods=['POST'])
def register():
    # Обработка регистрации

# WebSocket события
@socketio.on('send_message')
def handle_message(data):
    # Обработка сообщений
```

#### Модели данных (models.py)
- **Назначение**: Определение структуры базы данных
- **Технология**: SQLAlchemy ORM
- **Принципы**:
  - Нормализация данных
  - Связи между таблицами
  - Индексы для производительности

```python
# Пример модели
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    email = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    guilds = relationship('Guild', back_populates='owner')
    messages = relationship('Message', back_populates='user')
```

#### Модуль аутентификации (auth.py)
- **Назначение**: Безопасная аутентификация
- **Функции**:
  - Регистрация и вход пользователей
  - Хеширование паролей
  - CSRF защита
  - Rate limiting

```python
# Основные функции
def register_user(username, password, email):
    # Регистрация с валидацией

def login_user(username, password):
    # Аутентификация

def require_csrf(f):
    # CSRF защита

def rate_limited(limit_type):
    # Rate limiting
```

#### Модуль пользователей (users.py)
- **Назначение**: Управление пользователями и друзьями
- **Функции**:
  - CRUD операции с пользователями
  - Система друзей
  - Поиск пользователей
  - Профили

#### Модуль гильдий (guilds.py)
- **Назначение**: Управление серверами и каналами
- **Функции**:
  - Создание и управление гильдиями
  - Каналы и категории
  - Роли и права
  - Приглашения

#### Модуль сообщений (messages.py)
- **Назначение**: Обработка сообщений
- **Функции**:
  - Отправка и получение сообщений
  - Редактирование и удаление
  - Реакции и закрепление
  - Пагинация

#### Система кэширования (cache.py)
- **Назначение**: Оптимизация производительности
- **Функции**:
  - In-memory кэш с TTL
  - Инвалидация кэша
  - Автоматическая очистка

```python
# Пример использования кэша
@cached(ttl=300)
def get_user_data(user_id):
    # Кэшированная функция

def invalidate_user_cache(user_id):
    # Инвалидация кэша
```

## Frontend архитектура

### Структура компонентов

```
static/
├── style.css          # Стили и темы
└── script.js          # JavaScript логика

templates/
└── index.html         # HTML шаблон
```

### Основные компоненты

#### HTML структура (index.html)
- **Модульная разметка**
- **Семантические теги**
- **Доступность (a11y)**
- **Адаптивность**

```html
<!-- Основная структура -->
<div class="app-container">
  <div class="servers-panel">
    <!-- Панель серверов -->
  </div>
  <div class="channels-panel">
    <!-- Панель каналов -->
  </div>
  <div class="chat-area">
    <!-- Область чата -->
  </div>
</div>
```

#### CSS архитектура (style.css)
- **CSS переменные** для тем
- **Flexbox/Grid** для лейаутов
- **Анимации** и переходы
- **Медиа-запросы** для адаптивности

```css
/* CSS переменные для тем */
:root {
  --bg-primary: #ffffff;
  --text-primary: #000000;
  --accent-color: #5865f2;
}

.dark-theme {
  --bg-primary: #2c2f33;
  --text-primary: #ffffff;
}

/* Компонентный подход */
.message-item {
  /* Стили сообщения */
}

.channel-item {
  /* Стили канала */
}
```

#### JavaScript архитектура (script.js)
- **Объектно-ориентированный подход**
- **Модульная структура**
- **Обработка событий**
- **WebSocket интеграция**

```javascript
// Основной класс приложения
class MessengerApp {
  constructor() {
    this.socket = null;
    this.currentUser = null;
    this.currentRoom = null;
    this.initializeEventListeners();
    this.connectWebSocket();
  }
  
  // Методы для разных функций
  async login(username, password) { }
  async sendMessage(content) { }
  handleWebSocketEvents() { }
}
```

### Паттерны проектирования

#### Observer Pattern
- WebSocket события
- Обновления UI
- Уведомления

#### Module Pattern
- Разделение функциональности
- Инкапсуляция
- Переиспользование

#### Factory Pattern
- Создание элементов UI
- Обработчики событий
- API клиенты

## База данных

### Схема данных

```sql
-- Основные таблицы
users (id, username, password, email, created_at)
guilds (id, name, owner_id, created_at)
channels (id, name, guild_id, type, position)
messages (id, channel_id, user_id, content, timestamp)
files (id, filename, path, user_id, message_id)

-- Связующие таблицы
friendship (user_id, friend_id)
user_role (user_id, role_id, guild_id)
role_permission (role_id, permission_id)

-- Расширенные таблицы
custom_emojis (id, name, guild_id, file_path)
stickers (id, name, guild_id, file_path)
polls (id, message_id, question, options, expires_at)
poll_votes (id, poll_id, user_id, option_id)
```

### Принципы проектирования

#### Нормализация
- **1NF**: Атомарные значения
- **2NF**: Зависимость от полного ключа
- **3NF**: Отсутствие транзитивных зависимостей

#### Индексы
```sql
-- Индексы для производительности
CREATE INDEX idx_messages_channel_timestamp ON messages(channel_id, timestamp);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_guilds_owner ON guilds(owner_id);
```

#### Связи
- **One-to-Many**: User → Messages
- **Many-to-Many**: Users ↔ Friends
- **Self-referencing**: Messages → Replies

### Миграции

```python
# Пример миграции
def upgrade():
    op.create_table('polls',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('question', sa.String(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
```

## Real-time коммуникация

### WebSocket архитектура

#### Соединение
```javascript
// Клиент
const socket = io('http://localhost:5000');

// Сервер
@socketio.on('connect')
def handle_connect():
    print('Client connected')
```

#### События
```javascript
// Отправка события
socket.emit('send_message', {
  room: 'g:1:c:2',
  content: 'Hello!'
});

// Получение события
socket.on('new_message', (data) => {
  displayMessage(data);
});
```

#### Комнаты
```python
# Присоединение к комнате
@socketio.on('join_room')
def handle_join_room(data):
    room = data['room']
    join_room(room)
    emit('joined_room', {'room': room})

# Отправка в комнату
emit('new_message', message_data, room=room)
```

### Масштабирование WebSocket

#### Горизонтальное масштабирование
```python
# Redis для синхронизации между серверами
from flask_socketio import SocketIO

socketio = SocketIO(app, cors_allowed_origins="*",
                   message_queue='redis://localhost:6379')
```

#### Load Balancing
```nginx
# Nginx конфигурация
upstream websocket {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;
}

location /socket.io/ {
    proxy_pass http://websocket;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## Безопасность

### Многоуровневая защита

#### 1. Аутентификация
```python
# Хеширование паролей
from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password):
    return generate_password_hash(password)

def verify_password(password, hash):
    return check_password_hash(hash, password)
```

#### 2. Авторизация
```python
# Проверка прав
def require_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not check_user_permission(current_user, permission):
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

#### 3. CSRF защита
```python
# CSRF токены
def get_csrf_token():
    return secrets.token_hex(32)

def require_csrf(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-CSRF-Token')
        if not token or not verify_csrf_token(token):
            return jsonify({'error': 'Invalid CSRF token'}), 403
        return f(*args, **kwargs)
    return decorated_function
```

#### 4. Rate Limiting
```python
# Ограничение запросов
from functools import wraps
import time

def rate_limited(max_per_minute=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Логика rate limiting
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

#### 5. Валидация данных
```python
# Валидация входных данных
def validate_message_content(content):
    if not content or len(content.strip()) == 0:
        raise ValueError("Message content cannot be empty")
    if len(content) > 2000:
        raise ValueError("Message too long")
    return content.strip()
```

### Защита от атак

#### SQL Injection
- Использование ORM (SQLAlchemy)
- Параметризованные запросы
- Валидация входных данных

#### XSS
- Экранирование HTML
- Content Security Policy
- Валидация пользовательского ввода

#### CSRF
- CSRF токены
- SameSite cookies
- Проверка Referer

## Производительность

### Оптимизации Backend

#### Кэширование
```python
# In-memory кэш
class SimpleCache:
    def __init__(self, default_ttl=300):
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key):
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
        return None
    
    def set(self, key, value, ttl=None):
        if ttl is None:
            ttl = self.default_ttl
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
```

#### Пагинация
```python
# Пагинация сообщений
def get_messages(channel_id, limit=50, offset=0):
    return db.query(Message)\
        .filter_by(channel_id=channel_id)\
        .order_by(Message.timestamp.desc())\
        .offset(offset)\
        .limit(limit)\
        .all()
```

#### Индексы БД
```sql
-- Оптимизированные индексы
CREATE INDEX idx_messages_channel_timestamp ON messages(channel_id, timestamp DESC);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_guilds_owner ON guilds(owner_id);
```

### Оптимизации Frontend

#### Виртуализация
```javascript
// Виртуализация списка сообщений
class VirtualizedList {
  constructor(container, itemHeight) {
    this.container = container;
    this.itemHeight = itemHeight;
    this.visibleItems = Math.ceil(container.clientHeight / itemHeight) + 5;
  }
  
  renderVisibleItems() {
    // Рендеринг только видимых элементов
  }
}
```

#### Lazy Loading
```javascript
// Ленивая загрузка изображений
function lazyLoadImages() {
  const images = document.querySelectorAll('img[data-src]');
  const imageObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        img.src = img.dataset.src;
        img.removeAttribute('data-src');
        imageObserver.unobserve(img);
      }
    });
  });
  
  images.forEach(img => imageObserver.observe(img));
}
```

#### Debouncing
```javascript
// Оптимизация поиска
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

const debouncedSearch = debounce(searchUsers, 300);
```

## Масштабируемость

### Горизонтальное масштабирование

#### Stateless серверы
```python
# Без состояния - все данные в БД/кэше
class StatelessApp:
    def __init__(self):
        self.db = get_database_connection()
        self.cache = get_cache_connection()
    
    def handle_request(self, request):
        # Обработка без локального состояния
        pass
```

#### Load Balancing
```nginx
# Nginx конфигурация
upstream app_servers {
    server 127.0.0.1:5000 weight=1;
    server 127.0.0.1:5001 weight=1;
    server 127.0.0.1:5002 weight=1;
}

server {
    listen 80;
    location / {
        proxy_pass http://app_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Database Sharding
```python
# Шардирование по гильдиям
def get_shard_for_guild(guild_id):
    shard_count = 4
    return f"shard_{guild_id % shard_count}"

def get_messages_for_guild(guild_id):
    shard = get_shard_for_guild(guild_id)
    db = get_database_connection(shard)
    return db.query(Message).filter_by(guild_id=guild_id).all()
```

### Вертикальное масштабирование

#### Оптимизация запросов
```python
# Eager loading
def get_messages_with_users(channel_id):
    return db.query(Message)\
        .options(joinedload(Message.user))\
        .filter_by(channel_id=channel_id)\
        .all()
```

#### Connection Pooling
```python
# Пул соединений
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'postgresql://user:pass@host/db',
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30
)
```

## Мониторинг и логирование

### Логирование

```python
import logging
from logging.handlers import RotatingFileHandler

# Настройка логирования
def setup_logging(app):
    if not app.debug:
        file_handler = RotatingFileHandler(
            'logs/app.log', maxBytes=10240, backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')
```

### Метрики

```python
# Сбор метрик
import time
from functools import wraps

def track_metrics(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start_time
        
        # Отправка метрик
        send_metric('request_duration', duration, tags={'endpoint': f.__name__})
        return result
    return decorated_function
```

### Health Checks

```python
# Проверка здоровья
@app.route('/health')
def health_check():
    try:
        # Проверка БД
        db.session.execute('SELECT 1')
        
        # Проверка кэша
        cache.get('health_check')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
```

## Заключение

Архитектура Discord-like мессенджера построена на принципах:

1. **Модульности** - Легкость поддержки и развития
2. **Масштабируемости** - Возможность роста нагрузки
3. **Безопасности** - Многоуровневая защита
4. **Производительности** - Оптимизация на всех уровнях
5. **Тестируемости** - Полное покрытие тестами

Эта архитектура позволяет создавать надежное, производительное и безопасное приложение, способное обслуживать тысячи пользователей одновременно.



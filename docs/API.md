# API Документация

Полная документация REST API и WebSocket событий Discord-like мессенджера.

## Содержание

- [Аутентификация](#аутентификация)
- [Пользователи](#пользователи)
- [Гильдии](#гильдии)
- [Каналы](#каналы)
- [Сообщения](#сообщения)
- [Файлы](#файлы)
- [Поиск](#поиск)
- [Эмодзи и стикеры](#эмодзи-и-стикеры)
- [Опросы](#опросы)
- [WebSocket события](#websocket-события)
- [Коды ошибок](#коды-ошибок)

## Аутентификация

### Регистрация пользователя

```http
POST /api/register
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "username": "testuser",
  "password": "securepassword",
  "email": "test@example.com"
}
```

**Успешный ответ (201):**
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Ошибки:**
- `400` - Неверные данные (дублирующееся имя/email, слабый пароль)
- `500` - Внутренняя ошибка сервера

### Вход в систему

```http
POST /api/login
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "username": "testuser",
  "password": "securepassword"
}
```

**Успешный ответ (200):**
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com"
}
```

**Ошибки:**
- `401` - Неверные учетные данные
- `400` - Отсутствуют обязательные поля

### Выход из системы

```http
POST /api/logout
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
{
  "message": "Successfully logged out"
}
```

## Пользователи

### Получение списка пользователей

```http
GET /api/users
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
[
  {
    "id": 1,
    "username": "alice",
    "avatar": "avatar_url",
    "status": "online"
  }
]
```

### Поиск пользователей

```http
GET /api/search/users?q=alice
X-CSRF-Token: <token>
```

**Параметры:**
- `q` (обязательный) - Поисковый запрос (минимум 2 символа)

**Успешный ответ (200):**
```json
{
  "results": [
    {
      "username": "alice",
      "avatar": "avatar_url"
    }
  ],
  "count": 1
}
```

### Система друзей

#### Отправка запроса в друзья

```http
POST /api/friends/request
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "to": "alice"
}
```

**Успешный ответ (200):**
```json
{
  "message": "Friend request sent"
}
```

#### Принятие запроса в друзья

```http
POST /api/friends/accept
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "from": "alice"
}
```

#### Отклонение запроса в друзья

```http
POST /api/friends/decline
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "from": "alice"
}
```

#### Удаление из друзей

```http
POST /api/friends/remove
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "username": "alice"
}
```

#### Получение статуса друзей

```http
GET /api/friends/status
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
{
  "friends": ["alice", "bob"],
  "pending_in": ["charlie"],
  "pending_out": ["david"]
}
```

## Гильдии

### Создание гильдии

```http
POST /api/guilds
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "name": "My Server"
}
```

**Успешный ответ (201):**
```json
{
  "id": 1,
  "name": "My Server",
  "owner_id": 1,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Получение списка гильдий

```http
GET /api/guilds
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
[
  {
    "id": 1,
    "name": "My Server",
    "owner_id": 1,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Удаление гильдии

```http
DELETE /api/guilds/1
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
{
  "message": "Guild deleted successfully"
}
```

**Ошибки:**
- `403` - Недостаточно прав (только владелец может удалить)
- `404` - Гильдия не найдена

### Создание приглашения

```http
POST /api/guilds/1/invites
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "expires_hours": 24,
  "max_uses": 10
}
```

**Успешный ответ (201):**
```json
{
  "code": "abc123",
  "expires_at": "2024-01-02T00:00:00Z",
  "max_uses": 10,
  "uses": 0
}
```

### Присоединение по приглашению

```http
POST /api/invites/abc123/join
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
{
  "message": "Successfully joined guild",
  "guild_id": 1
}
```

## Каналы

### Создание канала

```http
POST /api/guilds/1/channels
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "name": "general",
  "type": "text",
  "category_id": 1
}
```

**Успешный ответ (201):**
```json
{
  "id": 1,
  "name": "general",
  "type": "text",
  "guild_id": 1,
  "position": 0,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Получение списка каналов

```http
GET /api/guilds/1/channels
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
[
  {
    "id": 1,
    "name": "general",
    "type": "text",
    "guild_id": 1,
    "position": 0
  }
]
```

### Обновление настроек канала

```http
PUT /api/channels/1
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "name": "new-name",
  "read_only": true
}
```

## Сообщения

### Получение сообщений с пагинацией

```http
GET /api/channels/1/messages?page=1&limit=50
X-CSRF-Token: <token>
```

**Параметры:**
- `page` (опциональный) - Номер страницы (по умолчанию 1)
- `limit` (опциональный) - Количество сообщений на странице (по умолчанию 50, максимум 100)

**Успешный ответ (200):**
```json
{
  "messages": [
    {
      "id": 1,
      "content": "Hello, world!",
      "username": "alice",
      "timestamp": "2024-01-01T00:00:00Z",
      "pinned": false,
      "files": [
        {
          "filename": "image.png",
          "path": "uploads/image.png"
        }
      ]
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 100,
    "pages": 2
  }
}
```

### Отправка сообщения

```http
POST /api/channels/1/messages
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "content": "Hello, everyone!"
}
```

**Успешный ответ (201):**
```json
{
  "id": 1,
  "content": "Hello, everyone!",
  "username": "alice",
  "timestamp": "2024-01-01T00:00:00Z",
  "pinned": false,
  "files": []
}
```

### Редактирование сообщения

```http
PUT /api/messages/1
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "content": "Updated message"
}
```

**Успешный ответ (200):**
```json
{
  "id": 1,
  "content": "Updated message",
  "username": "alice",
  "timestamp": "2024-01-01T00:00:00Z",
  "edited_at": "2024-01-01T00:01:00Z"
}
```

### Удаление сообщения

```http
DELETE /api/messages/1
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
{
  "message": "Message deleted successfully"
}
```

### Закрепление сообщения

```http
POST /api/messages/1/pin
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
{
  "message": "Message pinned successfully"
}
```

### Открепление сообщения

```http
POST /api/messages/1/unpin
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
{
  "message": "Message unpinned successfully"
}
```

## Файлы

### Загрузка файла

```http
POST /api/upload
Content-Type: multipart/form-data
X-CSRF-Token: <token>
```

**Параметры:**
- `file` (обязательный) - Файл для загрузки

**Ограничения:**
- Максимальный размер: 10 MB
- Разрешенные типы: изображения, документы, архивы

**Успешный ответ (201):**
```json
{
  "filename": "image.png",
  "path": "uploads/image.png",
  "size": 1024000,
  "mimetype": "image/png"
}
```

### Получение файла

```http
GET /uploads/image.png
```

**Успешный ответ (200):**
Файл в бинарном формате с соответствующими заголовками.

## Поиск

### Поиск по сообщениям

```http
GET /api/search/messages?q=hello&channel_id=1&limit=20
X-CSRF-Token: <token>
```

**Параметры:**
- `q` (обязательный) - Поисковый запрос
- `channel_id` (опциональный) - ID канала для поиска
- `limit` (опциональный) - Максимальное количество результатов (по умолчанию 20)

**Успешный ответ (200):**
```json
[
  {
    "id": 1,
    "content": "Hello, world!",
    "username": "alice",
    "channel_name": "general",
    "timestamp": "2024-01-01T00:00:00Z"
  }
]
```

## Эмодзи и стикеры

### Получение эмодзи гильдии

```http
GET /api/guilds/1/emojis
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
[
  {
    "id": "emoji_id",
    "name": "custom_emoji",
    "file_path": "emojis/emoji.png",
    "animated": false,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Создание кастомного эмодзи

```http
POST /api/guilds/1/emojis
Content-Type: multipart/form-data
X-CSRF-Token: <token>
```

**Параметры:**
- `name` (обязательный) - Имя эмодзи
- `file` (обязательный) - Файл эмодзи (PNG, JPG, GIF, WebP)

**Ограничения:**
- Только владелец гильдии может создавать эмодзи
- Максимальный размер файла: 256 KB
- Поддерживаются анимированные GIF

**Успешный ответ (201):**
```json
{
  "id": "emoji_id",
  "name": "custom_emoji",
  "file_path": "emojis/emoji.png",
  "animated": false
}
```

### Удаление эмодзи

```http
DELETE /api/emojis/emoji_id
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
{
  "success": true
}
```

### Получение стикеров гильдии

```http
GET /api/guilds/1/stickers
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
[
  {
    "id": "sticker_id",
    "name": "custom_sticker",
    "file_path": "stickers/sticker.png",
    "description": "A custom sticker",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Создание стикера

```http
POST /api/guilds/1/stickers
Content-Type: multipart/form-data
X-CSRF-Token: <token>
```

**Параметры:**
- `name` (обязательный) - Имя стикера
- `file` (обязательный) - Файл стикера (PNG, JPG, WebP)
- `description` (опциональный) - Описание стикера

**Успешный ответ (201):**
```json
{
  "id": "sticker_id",
  "name": "custom_sticker",
  "file_path": "stickers/sticker.png",
  "description": "A custom sticker"
}
```

## Опросы

### Создание опроса

```http
POST /api/messages/1/poll
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "question": "What is your favorite color?",
  "options": ["Red", "Blue", "Green"],
  "allow_multiple": false,
  "expires_hours": 24
}
```

**Параметры:**
- `question` (обязательный) - Вопрос опроса
- `options` (обязательный) - Массив вариантов ответов (2-10 вариантов)
- `allow_multiple` (опциональный) - Разрешить множественное голосование
- `expires_hours` (опциональный) - Время истечения в часах

**Успешный ответ (201):**
```json
{
  "id": "poll_id",
  "question": "What is your favorite color?",
  "options": [
    {"id": "1", "text": "Red", "votes": 0},
    {"id": "2", "text": "Blue", "votes": 0},
    {"id": "3", "text": "Green", "votes": 0}
  ],
  "expires_at": "2024-01-02T00:00:00Z",
  "allow_multiple": false
}
```

### Голосование в опросе

```http
POST /api/polls/poll_id/vote
Content-Type: application/json
X-CSRF-Token: <token>
```

**Тело запроса:**
```json
{
  "option_id": "1"
}
```

**Успешный ответ (200):**
```json
{
  "id": "poll_id",
  "question": "What is your favorite color?",
  "options": [
    {"id": "1", "text": "Red", "votes": 1},
    {"id": "2", "text": "Blue", "votes": 0},
    {"id": "3", "text": "Green", "votes": 0}
  ],
  "expires_at": "2024-01-02T00:00:00Z",
  "allow_multiple": false
}
```

### Получение опроса

```http
GET /api/messages/1/poll
X-CSRF-Token: <token>
```

**Успешный ответ (200):**
```json
{
  "id": "poll_id",
  "question": "What is your favorite color?",
  "options": [
    {"id": "1", "text": "Red", "votes": 1},
    {"id": "2", "text": "Blue", "votes": 0},
    {"id": "3", "text": "Green", "votes": 0}
  ],
  "expires_at": "2024-01-02T00:00:00Z",
  "allow_multiple": false,
  "user_votes": ["1"]
}
```

## WebSocket события

### События клиента

#### Присоединение к комнате
```javascript
socket.emit('join_room', { room: 'g:1:c:2' });
```

#### Покидание комнаты
```javascript
socket.emit('leave_room', { room: 'g:1:c:2' });
```

#### Отправка сообщения
```javascript
socket.emit('send_message', {
  room: 'g:1:c:2',
  content: 'Hello!',
  file: fileData  // опционально
});
```

#### Индикатор печати
```javascript
socket.emit('typing', { room: 'g:1:c:2' });
```

#### Остановка печати
```javascript
socket.emit('stop_typing', { room: 'g:1:c:2' });
```

#### Добавление реакции
```javascript
socket.emit('add_reaction', {
  room: 'g:1:c:2',
  message_id: 123,
  emoji: '👍'
});
```

#### Удаление реакции
```javascript
socket.emit('remove_reaction', {
  room: 'g:1:c:2',
  message_id: 123,
  emoji: '👍'
});
```

#### Закрепление сообщения
```javascript
socket.emit('pin_message', {
  room: 'g:1:c:2',
  message_id: 123
});
```

#### Открепление сообщения
```javascript
socket.emit('unpin_message', {
  room: 'g:1:c:2',
  message_id: 123
});
```

### События сервера

#### Новое сообщение
```javascript
socket.on('new_message', (data) => {
  console.log('New message:', data);
  // data содержит: id, content, username, timestamp, files, etc.
});
```

#### Сообщение отредактировано
```javascript
socket.on('message_edited', (data) => {
  console.log('Message edited:', data);
  // data содержит: id, content, edited_at
});
```

#### Сообщение удалено
```javascript
socket.on('message_deleted', (data) => {
  console.log('Message deleted:', data);
  // data содержит: id
});
```

#### Пользователь печатает
```javascript
socket.on('user_typing', (data) => {
  console.log('User typing:', data.username);
  // data содержит: username, room
});
```

#### Пользователь остановил печать
```javascript
socket.on('user_stopped_typing', (data) => {
  console.log('User stopped typing:', data.username);
  // data содержит: username, room
});
```

#### Реакция добавлена
```javascript
socket.on('reaction_added', (data) => {
  console.log('Reaction added:', data);
  // data содержит: message_id, emoji, username
});
```

#### Реакция удалена
```javascript
socket.on('reaction_removed', (data) => {
  console.log('Reaction removed:', data);
  // data содержит: message_id, emoji, username
});
```

#### Сообщение закреплено
```javascript
socket.on('message_pinned', (data) => {
  console.log('Message pinned:', data);
  // data содержит: message_id, room
});
```

#### Сообщение откреплено
```javascript
socket.on('message_unpinned', (data) => {
  console.log('Message unpinned:', data);
  // data содержит: message_id, room
});
```

#### История сообщений
```javascript
socket.on('messages_history', (messages) => {
  console.log('Messages history:', messages);
  // messages - массив сообщений
});
```

## Коды ошибок

### HTTP статус коды

- `200` - OK - Успешный запрос
- `201` - Created - Ресурс создан
- `400` - Bad Request - Неверные данные запроса
- `401` - Unauthorized - Требуется аутентификация
- `403` - Forbidden - Недостаточно прав
- `404` - Not Found - Ресурс не найден
- `409` - Conflict - Конфликт (например, дублирующиеся данные)
- `429` - Too Many Requests - Превышен лимит запросов
- `500` - Internal Server Error - Внутренняя ошибка сервера

### Формат ошибок

```json
{
  "error": "Описание ошибки",
  "code": "ERROR_CODE",
  "details": {
    "field": "Дополнительная информация"
  }
}
```

### Типичные ошибки

#### Аутентификация
- `INVALID_CREDENTIALS` - Неверные учетные данные
- `USER_NOT_FOUND` - Пользователь не найден
- `USER_ALREADY_EXISTS` - Пользователь уже существует
- `INVALID_EMAIL` - Неверный формат email
- `WEAK_PASSWORD` - Слабый пароль

#### Авторизация
- `INSUFFICIENT_PERMISSIONS` - Недостаточно прав
- `NOT_GUILD_OWNER` - Не владелец гильдии
- `NOT_CHANNEL_MEMBER` - Не участник канала

#### Валидация
- `INVALID_INPUT` - Неверные входные данные
- `MISSING_REQUIRED_FIELD` - Отсутствует обязательное поле
- `FILE_TOO_LARGE` - Файл слишком большой
- `INVALID_FILE_TYPE` - Неподдерживаемый тип файла

#### Ресурсы
- `GUILD_NOT_FOUND` - Гильдия не найдена
- `CHANNEL_NOT_FOUND` - Канал не найден
- `MESSAGE_NOT_FOUND` - Сообщение не найдено
- `POLL_NOT_FOUND` - Опрос не найден

#### Rate Limiting
- `RATE_LIMIT_EXCEEDED` - Превышен лимит запросов
- `TOO_MANY_MESSAGES` - Слишком много сообщений
- `TOO_MANY_FRIEND_REQUESTS` - Слишком много запросов в друзья

## Примеры использования

### JavaScript клиент

```javascript
// Подключение к WebSocket
const socket = io();

// Аутентификация
socket.emit('authenticate', { token: 'user_token' });

// Присоединение к каналу
socket.emit('join_room', { room: 'g:1:c:2' });

// Отправка сообщения
socket.emit('send_message', {
  room: 'g:1:c:2',
  content: 'Hello, world!'
});

// Обработка новых сообщений
socket.on('new_message', (message) => {
  displayMessage(message);
});

// REST API запросы
async function sendMessage(channelId, content) {
  const response = await fetch(`/api/channels/${channelId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': getCsrfToken()
    },
    body: JSON.stringify({ content })
  });
  
  if (response.ok) {
    const message = await response.json();
    return message;
  } else {
    throw new Error('Failed to send message');
  }
}
```

### Python клиент

```python
import requests
import socketio

# REST API
def send_message(channel_id, content, csrf_token):
    response = requests.post(
        f'http://localhost:5000/api/channels/{channel_id}/messages',
        json={'content': content},
        headers={'X-CSRF-Token': csrf_token}
    )
    return response.json()

# WebSocket
sio = socketio.Client()

@sio.event
def connect():
    print('Connected to server')

@sio.event
def new_message(data):
    print(f'New message: {data}')

sio.connect('http://localhost:5000')
sio.emit('join_room', {'room': 'g:1:c:2'})
sio.emit('send_message', {
    'room': 'g:1:c:2',
    'content': 'Hello from Python!'
})
```

## Лимиты и ограничения

### Rate Limiting
- API запросы: 100 запросов в минуту на IP
- WebSocket события: 60 событий в минуту на пользователя
- Загрузка файлов: 10 файлов в минуту на пользователя

### Размеры
- Максимальный размер сообщения: 2000 символов
- Максимальный размер файла: 10 MB
- Максимальное количество друзей: 1000
- Максимальное количество гильдий: 100

### Ограничения
- Максимальное количество каналов в гильдии: 500
- Максимальное количество сообщений в канале: 10000
- Максимальное количество вариантов в опросе: 10
- Максимальное время жизни опроса: 7 дней



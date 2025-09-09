# Руководство по развертыванию

Подробное руководство по развертыванию Discord-like мессенджера в различных окружениях.

## Содержание

- [Локальная разработка](#локальная-разработка)
- [Продакшен развертывание](#продакшен-развертывание)
- [Docker развертывание](#docker-развертывание)
- [Облачные платформы](#облачные-платформы)
- [Мониторинг и логирование](#мониторинг-и-логирование)
- [Безопасность в продакшене](#безопасность-в-продакшене)
- [Масштабирование](#масштабирование)
- [Резервное копирование](#резервное-копирование)

## Локальная разработка

### Системные требования

- **Python**: 3.8 или выше
- **pip**: Последняя версия
- **Git**: Для клонирования репозитория
- **Браузер**: Современный браузер с поддержкой WebSocket

### Установка

#### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd discord-messenger
```

#### 2. Создание виртуального окружения
```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. Установка зависимостей
```bash
pip install -r requirements.txt

# Для разработки
pip install -r tests/requirements.txt
```

#### 4. Настройка окружения
```bash
# Создание файла конфигурации
cp .env.example .env

# Редактирование конфигурации
nano .env
```

#### 5. Инициализация базы данных
```bash
python backend/init_permissions.py
```

#### 6. Запуск приложения
```bash
python backend/app.py
```

Приложение будет доступно по адресу: `http://localhost:5000`

### Конфигурация для разработки

#### Переменные окружения (.env)
```bash
# Основные настройки
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-development-secret-key

# База данных
DATABASE_URL=sqlite:///oleg_messenger.db

# Кэш
REDIS_URL=redis://localhost:6379/0

# Файлы
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=10485760  # 10MB

# Безопасность
CSRF_SECRET_KEY=your-csrf-secret
RATE_LIMIT_STORAGE_URL=memory://
```

#### Настройки Flask
```python
# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
```

## Продакшен развертывание

### Системные требования

- **ОС**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **Python**: 3.8+
- **RAM**: Минимум 1GB, рекомендуется 2GB+
- **CPU**: 1-2 ядра
- **Диск**: 10GB+ свободного места
- **Сеть**: Стабильное подключение к интернету

### Установка на сервер

#### 1. Подготовка сервера
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и зависимостей
sudo apt install python3 python3-pip python3-venv nginx supervisor -y

# Создание пользователя для приложения
sudo useradd -m -s /bin/bash messenger
sudo usermod -aG sudo messenger
```

#### 2. Развертывание приложения
```bash
# Переключение на пользователя приложения
sudo su - messenger

# Клонирование репозитория
git clone <repository-url> /home/messenger/app
cd /home/messenger/app

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
pip install gunicorn  # WSGI сервер
```

#### 3. Настройка базы данных
```bash
# Установка PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Создание базы данных
sudo -u postgres createdb messenger_db
sudo -u postgres createuser messenger_user
sudo -u postgres psql -c "ALTER USER messenger_user PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE messenger_db TO messenger_user;"
```

#### 4. Конфигурация приложения
```bash
# Создание конфигурации продакшена
cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
DATABASE_URL=postgresql://messenger_user:secure_password@localhost/messenger_db
REDIS_URL=redis://localhost:6379/0
UPLOAD_FOLDER=/home/messenger/app/uploads
MAX_CONTENT_LENGTH=10485760
CSRF_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
EOF

# Создание директории для загрузок
mkdir -p uploads
chmod 755 uploads

# Инициализация базы данных
python backend/init_permissions.py
```

#### 5. Настройка Gunicorn
```bash
# Создание конфигурации Gunicorn
cat > gunicorn.conf.py << EOF
bind = "127.0.0.1:5000"
workers = 4
worker_class = "eventlet"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
EOF
```

#### 6. Настройка Supervisor
```bash
# Создание конфигурации Supervisor
sudo cat > /etc/supervisor/conf.d/messenger.conf << EOF
[program:messenger]
command=/home/messenger/app/venv/bin/gunicorn --config gunicorn.conf.py backend.app:app
directory=/home/messenger/app
user=messenger
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/messenger.log
environment=PATH="/home/messenger/app/venv/bin"
EOF

# Перезапуск Supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start messenger
```

#### 7. Настройка Nginx
```bash
# Создание конфигурации Nginx
sudo cat > /etc/nginx/sites-available/messenger << EOF
server {
    listen 80;
    server_name your-domain.com;

    # Основное приложение
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket поддержка
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Статические файлы
    location /static/ {
        alias /home/messenger/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Загруженные файлы
    location /uploads/ {
        alias /home/messenger/app/uploads/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Безопасность
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
EOF

# Активация сайта
sudo ln -s /etc/nginx/sites-available/messenger /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 8. Настройка SSL (Let's Encrypt)
```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx -y

# Получение SSL сертификата
sudo certbot --nginx -d your-domain.com

# Автоматическое обновление
sudo crontab -e
# Добавить строку:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## Docker развертывание

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя приложения
RUN useradd -m -s /bin/bash messenger

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директорий
RUN mkdir -p uploads logs && \
    chown -R messenger:messenger /app

# Переключение на пользователя приложения
USER messenger

# Открытие порта
EXPOSE 5000

# Переменные окружения
ENV FLASK_APP=backend/app.py
ENV FLASK_ENV=production

# Команда запуска
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "eventlet", "-w", "4", "backend.app:app"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://messenger:password@db:5432/messenger_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=messenger_db
      - POSTGRES_USER=messenger
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Запуск с Docker

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f app

# Остановка
docker-compose down

# Обновление
docker-compose pull
docker-compose up -d
```

## Облачные платформы

### Heroku

#### 1. Подготовка приложения
```bash
# Создание Procfile
echo "web: gunicorn --bind 0.0.0.0:\$PORT --worker-class eventlet -w 4 backend.app:app" > Procfile

# Создание runtime.txt
echo "python-3.9.7" > runtime.txt

# Создание requirements.txt для Heroku
cat > requirements.txt << EOF
Flask==2.0.1
Flask-SocketIO==5.1.1
SQLAlchemy==1.4.23
psycopg2-binary==2.9.1
gunicorn==20.1.0
eventlet==0.33.0
python-dotenv==0.19.0
EOF
```

#### 2. Развертывание
```bash
# Установка Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Логин в Heroku
heroku login

# Создание приложения
heroku create your-messenger-app

# Добавление PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Добавление Redis
heroku addons:create heroku-redis:hobby-dev

# Установка переменных окружения
heroku config:set SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
heroku config:set FLASK_ENV=production

# Развертывание
git push heroku main

# Запуск миграций
heroku run python backend/init_permissions.py
```

### AWS

#### 1. Elastic Beanstalk
```bash
# Установка EB CLI
pip install awsebcli

# Инициализация
eb init

# Создание окружения
eb create production

# Развертывание
eb deploy
```

#### 2. ECS с Fargate
```yaml
# task-definition.json
{
  "family": "messenger-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "messenger",
      "image": "your-account.dkr.ecr.region.amazonaws.com/messenger:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "FLASK_ENV",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/messenger",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Platform

#### 1. App Engine
```yaml
# app.yaml
runtime: python39

env_variables:
  FLASK_ENV: production
  DATABASE_URL: postgresql://user:pass@/db?host=/cloudsql/project:region:instance

automatic_scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 0.6

handlers:
- url: /.*
  script: auto
```

#### 2. Cloud Run
```bash
# Сборка и развертывание
gcloud builds submit --tag gcr.io/PROJECT-ID/messenger
gcloud run deploy --image gcr.io/PROJECT-ID/messenger --platform managed
```

## Мониторинг и логирование

### Настройка логирования

```python
# backend/logging_config.py
import logging
import logging.handlers
import os

def setup_logging(app):
    if not app.debug:
        # Создание директории для логов
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Настройка файлового логгера
        file_handler = logging.handlers.RotatingFileHandler(
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

### Мониторинг с Prometheus

```python
# backend/metrics.py
from prometheus_client import Counter, Histogram, generate_latest
import time

# Метрики
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - request.start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.endpoint).inc()
    REQUEST_DURATION.observe(duration)
    return response

@app.route('/metrics')
def metrics():
    return generate_latest()
```

### Health Checks

```python
# backend/health.py
@app.route('/health')
def health_check():
    try:
        # Проверка базы данных
        db.session.execute('SELECT 1')
        
        # Проверка кэша
        cache.get('health_check')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
```

## Безопасность в продакшене

### Настройка файрвола

```bash
# UFW (Ubuntu)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5000/tcp  # Блокировка прямого доступа к приложению
```

### Настройка SSL

```bash
# Nginx SSL конфигурация
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Современные SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Остальная конфигурация...
}
```

### Безопасность базы данных

```bash
# PostgreSQL настройки безопасности
sudo nano /etc/postgresql/13/main/postgresql.conf

# Изменения:
listen_addresses = 'localhost'
ssl = on
password_encryption = scram-sha-256

# Настройка pg_hba.conf
sudo nano /etc/postgresql/13/main/pg_hba.conf

# Добавить:
local   all             all                                     scram-sha-256
host    all             all             127.0.0.1/32            scram-sha-256
```

## Масштабирование

### Горизонтальное масштабирование

#### Load Balancer конфигурация
```nginx
# nginx.conf
upstream messenger_backend {
    least_conn;
    server 127.0.0.1:5000 weight=1;
    server 127.0.0.1:5001 weight=1;
    server 127.0.0.1:5002 weight=1;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://messenger_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /socket.io/ {
        proxy_pass http://messenger_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

#### Redis для синхронизации
```python
# backend/redis_config.py
from flask_socketio import SocketIO
import redis

# Redis для синхронизации между серверами
redis_client = redis.Redis(host='localhost', port=6379, db=0)

socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    message_queue='redis://localhost:6379'
)
```

### Вертикальное масштабирование

#### Оптимизация Gunicorn
```python
# gunicorn.conf.py
bind = "127.0.0.1:5000"
workers = 8  # Увеличить количество воркеров
worker_class = "eventlet"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True

# Оптимизация памяти
worker_tmp_dir = "/dev/shm"
```

#### Оптимизация базы данных
```sql
-- PostgreSQL настройки
-- postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

## Резервное копирование

### Автоматическое резервное копирование

```bash
#!/bin/bash
# backup.sh

# Настройки
DB_NAME="messenger_db"
DB_USER="messenger_user"
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Создание резервной копии базы данных
pg_dump -h localhost -U $DB_USER $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Создание резервной копии файлов
tar -czf $BACKUP_DIR/uploads_backup_$DATE.tar.gz /home/messenger/app/uploads

# Удаление старых резервных копий (старше 30 дней)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

# Отправка в облачное хранилище (опционально)
# aws s3 cp $BACKUP_DIR/db_backup_$DATE.sql s3://your-backup-bucket/
```

### Настройка cron
```bash
# Добавление в crontab
crontab -e

# Ежедневное резервное копирование в 2:00
0 2 * * * /home/messenger/backup.sh
```

### Восстановление из резервной копии

```bash
# Восстановление базы данных
psql -h localhost -U messenger_user messenger_db < /backups/db_backup_20240101_020000.sql

# Восстановление файлов
tar -xzf /backups/uploads_backup_20240101_020000.tar.gz -C /
```

## Заключение

Это руководство покрывает основные сценарии развертывания Discord-like мессенджера:

1. **Локальная разработка** - Быстрый старт для разработчиков
2. **Продакшен** - Надежное развертывание на сервере
3. **Docker** - Контейнеризованное развертывание
4. **Облачные платформы** - Развертывание в облаке
5. **Мониторинг** - Отслеживание состояния приложения
6. **Безопасность** - Защита в продакшене
7. **Масштабирование** - Рост нагрузки
8. **Резервное копирование** - Защита данных

Выберите подходящий вариант развертывания в зависимости от ваших требований и ресурсов.



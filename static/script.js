class OlegMessenger {
    constructor() {
        this.socket = null;
        this.currentUser = null;
        this.currentRoom = null;
        this.typingUsers = new Set();
        this.typingTimeout = null;
        this.isPageVisible = true;
        this.initializeEventListeners();
        this.initializeTheme();
        this.initializeNotifications();
    }

    initializeEventListeners() {
        // Кнопки входа и регистрации
        document.getElementById('login-btn').addEventListener('click', () => this.login());
        document.getElementById('register-btn').addEventListener('click', () => this.register());
        document.getElementById('logout-btn').addEventListener('click', () => this.logout());
        document.getElementById('theme-toggle-btn').addEventListener('click', () => this.toggleTheme());
        
        // Поле ввода имени пользователя
        document.getElementById('username-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.login();
        });
        // Новое: поле пароля
        document.getElementById('password-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.login();
        });
        
        // Создание комнаты
        document.getElementById('create-room-btn').addEventListener('click', () => this.createRoom());
        document.getElementById('new-room-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.createRoom();
        });
        
        // Отправка сообщения
        document.getElementById('send-btn').addEventListener('click', () => this.sendMessage());
        document.getElementById('message-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
        
        // Индикатор печати
        document.getElementById('message-input').addEventListener('input', () => this.handleTyping());
        
        // Эмодзи
        document.getElementById('emoji-btn').addEventListener('click', () => this.toggleEmojiPicker());
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#emoji-picker') && !e.target.closest('#emoji-btn')) {
                this.hideEmojiPicker();
            }
        });
        
        // Отслеживание видимости страницы
        document.addEventListener('visibilitychange', () => {
            this.isPageVisible = !document.hidden;
            if (this.isPageVisible) {
                // Очищаем уведомления при возвращении на страницу
                this.clearNotifications();
            }
        });
        
        // Поиск по сообщениям
        document.getElementById('search-btn').addEventListener('click', () => this.searchMessages());
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchMessages();
        });
        document.getElementById('clear-search-btn').addEventListener('click', () => this.clearSearch());
        
        // Отправка файлов
        document.getElementById('file-btn').addEventListener('click', () => {
            document.getElementById('file-input').click();
        });
        document.getElementById('file-input').addEventListener('change', (e) => this.handleFileSelect(e));
    }

    async login() {
        const username = document.getElementById('username-input').value.trim();
        const password = document.getElementById('password-input').value;
        if (!username || !password) {
            this.showError('Введите имя пользователя и пароль');
            return;
        }

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            
            if (data.success) {
                this.currentUser = data;
                this.showChatScreen();
                this.initializeSocket();
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            this.showError('Ошибка подключения к серверу');
        }
    }

    async register() {
        const username = document.getElementById('username-input').value.trim();
        const password = document.getElementById('password-input').value;
        if (!username || !password) {
            this.showError('Введите имя пользователя и пароль');
            return;
        }

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            
            if (data.success) {
                this.currentUser = data;
                this.showChatScreen();
                this.initializeSocket();
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            this.showError('Ошибка подключения к серверу');
        }
    }

    showChatScreen() {
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('chat-screen').classList.remove('hidden');
        document.getElementById('current-username').textContent = this.currentUser.username;
        this.loadUsers();
        this.loadRooms();
    }

    showLoginScreen() {
        document.getElementById('chat-screen').classList.add('hidden');
        document.getElementById('login-screen').classList.remove('hidden');
        document.getElementById('username-input').value = '';
        this.currentUser = null;
        this.currentRoom = null;
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
    }

    showError(message) {
        const errorElement = document.getElementById('login-error');
        errorElement.textContent = message;
        setTimeout(() => {
            errorElement.textContent = '';
        }, 5000);
    }

    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Подключен к серверу');
        });

        this.socket.on('disconnect', () => {
            console.log('Отключен от сервера');
        });

        this.socket.on('new_message', (data) => {
            this.addMessage(data);
            
            // Показываем уведомление, если сообщение не от текущего пользователя
            // и страница не активна или сообщение не в текущей комнате
            if (data.username !== this.currentUser.username && 
                (!this.isPageVisible || data.room !== this.currentRoom)) {
                this.showNotification(data);
            }
        });

        this.socket.on('user_status', (data) => {
            this.updateUserStatus(data);
        });

        this.socket.on('room_joined', (data) => {
            this.updateRoomUsers();
        });

        this.socket.on('room_left', (data) => {
            this.updateRoomUsers();
        });

        this.socket.on('messages_history', (messages) => {
            this.loadMessages(messages);
        });

        this.socket.on('user_typing', (data) => {
            this.updateTypingIndicator(data);
        });

        this.socket.on('message_edited', (data) => {
            this.updateMessage(data);
        });

        this.socket.on('message_deleted', (data) => {
            this.removeMessage(data.message_id);
        });
    }

    async loadUsers() {
        try {
            const response = await fetch('/api/users');
            const users = await response.json();
            this.displayUsers(users);
        } catch (error) {
            console.error('Ошибка загрузки пользователей:', error);
        }
    }

    displayUsers(users) {
        const usersList = document.getElementById('users-list');
        usersList.innerHTML = '';
        
        // Сортируем пользователей: сначала онлайн, потом оффлайн
        const sortedUsers = users.sort((a, b) => {
            if (a.online && !b.online) return -1;
            if (!a.online && b.online) return 1;
            return a.username.localeCompare(b.username);
        });
        
        sortedUsers.forEach(user => {
            const userElement = document.createElement('div');
            userElement.className = `user-item ${user.online ? 'online' : 'offline'}`;
            
            const joinDate = new Date(user.joined_at).toLocaleDateString('ru-RU');
            
            userElement.innerHTML = `
                <div class="user-status ${user.online ? '' : 'offline'}"></div>
                <div class="user-info">
                    <span class="username">${user.username}</span>
                    <span class="user-details">${user.online ? 'В сети' : 'Не в сети'} • с ${joinDate}</span>
                </div>
            `;
            usersList.appendChild(userElement);
        });
    }

    updateUserStatus(data) {
        const userItems = document.querySelectorAll('.user-item');
        userItems.forEach(item => {
            const usernameElement = item.querySelector('.username');
            if (usernameElement && usernameElement.textContent === data.username) {
                const status = item.querySelector('.user-status');
                const details = item.querySelector('.user-details');
                
                status.className = `user-status ${data.online ? '' : 'offline'}`;
                item.className = `user-item ${data.online ? 'online' : 'offline'}`;
                
                // Обновляем текст статуса
                const joinDate = details.textContent.split('• с ')[1];
                details.textContent = `${data.online ? 'В сети' : 'Не в сети'} • с ${joinDate}`;
            }
        });
        
        // Пересортируем список пользователей
        this.loadUsers();
    }

    async loadRooms() {
        try {
            const response = await fetch('/api/rooms');
            const rooms = await response.json();
            this.displayRooms(rooms);
        } catch (error) {
            console.error('Ошибка загрузки комнат:', error);
        }
    }

    displayRooms(rooms) {
        const roomsList = document.getElementById('rooms-list');
        roomsList.innerHTML = '';
        
        rooms.forEach(room => {
            const roomElement = document.createElement('div');
            roomElement.className = 'room-item';
            roomElement.textContent = `# ${room}`;
            roomElement.addEventListener('click', () => this.joinRoom(room));
            roomsList.appendChild(roomElement);
        });
    }

    createRoom() {
        const roomName = document.getElementById('new-room-input').value.trim();
        if (!roomName) return;
        
        this.joinRoom(roomName);
        document.getElementById('new-room-input').value = '';
    }

    joinRoom(roomName) {
        if (this.currentRoom) {
            this.socket.emit('leave_room', { room: this.currentRoom });
        }
        
        this.currentRoom = roomName;
        this.socket.emit('join_room', { room: roomName });
        
        // Обновляем UI
        document.getElementById('current-room').textContent = `# ${roomName}`;
        document.getElementById('message-input').disabled = false;
        document.getElementById('send-btn').disabled = false;
        document.getElementById('search-input').disabled = false;
        document.getElementById('search-btn').disabled = false;
        
        // Подсвечиваем активную комнату
        document.querySelectorAll('.room-item').forEach(item => {
            item.classList.remove('active');
            if (item.textContent.trim() === `# ${roomName}`) {
                item.classList.add('active');
            }
        });
        
        // Загружаем историю сообщений
        this.socket.emit('get_messages', { room: roomName });
    }

    sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        const fileInput = document.getElementById('file-input');
        const file = fileInput.files[0];
        
        if (!message && !file) return;
        if (!this.currentRoom) return;
        
        if (file) {
            // Отправляем файл
            this.sendFile(file);
        }
        
        if (message) {
            // Отправляем текстовое сообщение
            this.socket.emit('send_message', {
                room: this.currentRoom,
                message: message
            });
        }
        
        messageInput.value = '';
    }

    addMessage(data) {
        const messagesList = document.getElementById('messages-list');
        const messageElement = document.createElement('div');
        messageElement.className = `message ${data.username === this.currentUser.username ? 'own' : 'other'}`;
        messageElement.dataset.messageId = data.id;

        const timestamp = new Date(data.timestamp).toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
        });

        const isOwnMessage = data.username === this.currentUser.username;
        const editButton = isOwnMessage ? '<button class="message-action-btn edit-btn" title="Редактировать"><i class="fas fa-edit"></i></button>' : '';
        const deleteButton = isOwnMessage ? '<button class="message-action-btn delete-btn" title="Удалить"><i class="fas fa-trash"></i></button>' : '';
        const editedIndicator = data.edited ? '<span class="edited-indicator">(изменено)</span>' : '';

        let fileContent = '';
        let messageContent = this.escapeHtml(data.message);
        if (data.file) {
            if (data.file.type && data.file.type.startsWith('image/')) {
                fileContent = `<div class="message-file"><img src="${data.file.url}" alt="${data.file.name}" class="message-image"></div>`;
                // Если текст пустой, не показываем "📎 Файл: ...", только картинку
                if (!messageContent) messageContent = '';
            } else {
                fileContent = `<div class="message-file"><a href="${data.file.url}" target="_blank" class="file-link"><i class="fas fa-file"></i> ${data.file.name}</a></div>`;
            }
        }

        // Аватар — первая буква ника
        const avatar = `<div class="avatar">${data.username[0].toUpperCase()}</div>`;
        // Имя и время в одну строку
        const header = `<div class="message-header"><span class="message-username">${data.username}</span><span class="message-time">${timestamp}</span>${editedIndicator}</div>`;
        // Контент
        const contentBlock = `<div class="message-content-block">${header}${messageContent ? `<div class="message-content">${messageContent}</div>` : ''}${fileContent}</div>`;

        messageElement.innerHTML = `${avatar}${contentBlock}`;

        // Добавляем обработчики для кнопок
        if (isOwnMessage) {
            const editBtn = messageElement.querySelector('.edit-btn');
            const deleteBtn = messageElement.querySelector('.delete-btn');
            if (editBtn) editBtn.addEventListener('click', () => this.editMessage(data.id, data.message));
            if (deleteBtn) deleteBtn.addEventListener('click', () => this.deleteMessage(data.id));
        }
        // Добавляем обработчик для увеличения картинки
        const img = messageElement.querySelector('.message-image');
        if (img) {
            img.addEventListener('click', () => {
                window.open(img.src, '_blank');
            });
        }
        messagesList.appendChild(messageElement);
        messagesList.scrollTop = messagesList.scrollHeight;
    }

    loadMessages(messages) {
        const messagesList = document.getElementById('messages-list');
        messagesList.innerHTML = '';
        
        messages.forEach(message => {
            this.addMessage(message);
        });
    }

    updateRoomUsers() {
        // В реальном приложении здесь бы загружались пользователи комнаты
        document.getElementById('room-users-count').textContent = 'Пользователи обновляются...';
    }

    logout() {
        this.showLoginScreen();
    }

    handleTyping() {
        if (!this.currentRoom) return;
        
        // Отправляем сигнал о начале печати
        this.socket.emit('typing_start', { room: this.currentRoom });
        
        // Очищаем предыдущий таймаут
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }
        
        // Устанавливаем таймаут для остановки индикатора печати
        this.typingTimeout = setTimeout(() => {
            this.socket.emit('typing_stop', { room: this.currentRoom });
        }, 1000);
    }

    updateTypingIndicator(data) {
        if (data.typing) {
            this.typingUsers.add(data.username);
        } else {
            this.typingUsers.delete(data.username);
        }
        
        this.displayTypingIndicator();
    }

    displayTypingIndicator() {
        const messagesList = document.getElementById('messages-list');
        let typingIndicator = document.getElementById('typing-indicator');
        
        // Удаляем старый индикатор
        if (typingIndicator) {
            typingIndicator.remove();
        }
        
        // Показываем новый индикатор, если есть печатающие пользователи
        if (this.typingUsers.size > 0) {
            typingIndicator = document.createElement('div');
            typingIndicator.id = 'typing-indicator';
            typingIndicator.className = 'typing-indicator';
            
            const users = Array.from(this.typingUsers);
            let text = '';
            if (users.length === 1) {
                text = `${users[0]} печатает...`;
            } else if (users.length === 2) {
                text = `${users[0]} и ${users[1]} печатают...`;
            } else {
                text = `${users[0]} и еще ${users.length - 1} печатают...`;
            }
            
            typingIndicator.innerHTML = `
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <span class="typing-text">${text}</span>
            `;
            
            messagesList.appendChild(typingIndicator);
            messagesList.scrollTop = messagesList.scrollHeight;
        }
    }

    initializeTheme() {
        const savedTheme = localStorage.getItem('oleg-messenger-theme') || 'light';
        this.setTheme(savedTheme);
    }

    toggleTheme() {
        const currentTheme = document.body.classList.contains('dark-theme') ? 'dark' : 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
        localStorage.setItem('oleg-messenger-theme', newTheme);
    }

    setTheme(theme) {
        const body = document.body;
        const themeIcon = document.querySelector('#theme-toggle-btn i');
        
        if (theme === 'dark') {
            body.classList.add('dark-theme');
            themeIcon.className = 'fas fa-sun';
        } else {
            body.classList.remove('dark-theme');
            themeIcon.className = 'fas fa-moon';
        }
    }

    toggleEmojiPicker() {
        const emojiPicker = document.getElementById('emoji-picker');
        if (emojiPicker.classList.contains('hidden')) {
            this.showEmojiPicker();
        } else {
            this.hideEmojiPicker();
        }
    }

    showEmojiPicker() {
        const emojiPicker = document.getElementById('emoji-picker');
        emojiPicker.classList.remove('hidden');
        
        // Добавляем обработчики для эмодзи
        emojiPicker.querySelectorAll('.emoji').forEach(emoji => {
            emoji.addEventListener('click', () => this.insertEmoji(emoji.dataset.emoji));
        });
    }

    hideEmojiPicker() {
        const emojiPicker = document.getElementById('emoji-picker');
        emojiPicker.classList.add('hidden');
    }

    insertEmoji(emoji) {
        const messageInput = document.getElementById('message-input');
        const cursorPos = messageInput.selectionStart;
        const textBefore = messageInput.value.substring(0, cursorPos);
        const textAfter = messageInput.value.substring(messageInput.selectionEnd);
        
        messageInput.value = textBefore + emoji + textAfter;
        messageInput.selectionStart = messageInput.selectionEnd = cursorPos + emoji.length;
        messageInput.focus();
        
        this.hideEmojiPicker();
    }

    editMessage(messageId, currentContent) {
        const newContent = prompt('Редактировать сообщение:', currentContent);
        if (newContent !== null && newContent.trim() !== '' && newContent !== currentContent) {
            this.socket.emit('edit_message', {
                room: this.currentRoom,
                message_id: messageId,
                new_content: newContent.trim()
            });
        }
    }

    deleteMessage(messageId) {
        if (confirm('Вы уверены, что хотите удалить это сообщение?')) {
            this.socket.emit('delete_message', {
                room: this.currentRoom,
                message_id: messageId
            });
        }
    }

    updateMessage(data) {
        const messageElement = document.querySelector(`[data-message-id="${data.message_id}"]`);
        if (messageElement) {
            const contentElement = messageElement.querySelector('.message-content');
            const timeElement = messageElement.querySelector('.message-time');
            
            contentElement.textContent = data.new_content;
            
            // Обновляем время редактирования
            const editedAt = new Date(data.edited_at).toLocaleTimeString('ru-RU', {
                hour: '2-digit',
                minute: '2-digit'
            });
            
            // Убираем старое время и добавляем новое
            const timeText = timeElement.textContent.split('(')[0].trim();
            timeElement.innerHTML = `${timeText} <span class="edited-indicator">(изменено в ${editedAt})</span>`;
        }
    }

    removeMessage(messageId) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageElement) {
            messageElement.remove();
        }
    }

    initializeNotifications() {
        // Запрашиваем разрешение на уведомления
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }

    showNotification(data) {
        // Проверяем поддержку уведомлений
        if (!('Notification' in window)) {
            return;
        }

        // Проверяем разрешение
        if (Notification.permission !== 'granted') {
            return;
        }

        // Создаем уведомление
        const notification = new Notification(`Oleg Messenger - ${data.room}`, {
            body: `${data.username}: ${data.message}`,
            icon: '/static/favicon.ico',
            tag: `message-${data.room}`,
            requireInteraction: false
        });

        // Автоматически закрываем уведомление через 5 секунд
        setTimeout(() => {
            notification.close();
        }, 5000);

        // При клике на уведомление переходим к сообщению
        notification.onclick = () => {
            window.focus();
            if (data.room !== this.currentRoom) {
                this.joinRoom(data.room);
            }
            notification.close();
        };
    }

    clearNotifications() {
        // Очищаем все уведомления при возвращении на страницу
        if ('Notification' in window) {
            // Закрываем все уведомления
            navigator.serviceWorker?.getRegistrations().then(registrations => {
                registrations.forEach(registration => {
                    registration.getNotifications().then(notifications => {
                        notifications.forEach(notification => notification.close());
                    });
                });
            });
        }
    }

    searchMessages() {
        const searchTerm = document.getElementById('search-input').value.trim();
        if (!searchTerm || !this.currentRoom) return;

        const messages = document.querySelectorAll('.message');
        let foundCount = 0;

        messages.forEach(message => {
            const content = message.querySelector('.message-content').textContent.toLowerCase();
            const username = message.querySelector('.message-header span').textContent.toLowerCase();
            
            if (content.includes(searchTerm.toLowerCase()) || username.includes(searchTerm.toLowerCase())) {
                message.classList.add('search-highlight');
                message.scrollIntoView({ behavior: 'smooth', block: 'center' });
                foundCount++;
            } else {
                message.classList.remove('search-highlight');
            }
        });

        // Показываем результаты поиска
        this.showSearchResults(foundCount, searchTerm);
    }

    showSearchResults(count, term) {
        const clearBtn = document.getElementById('clear-search-btn');
        clearBtn.classList.remove('hidden');
        
        // Обновляем заголовок комнаты с результатами поиска
        const roomTitle = document.getElementById('current-room');
        if (count > 0) {
            roomTitle.textContent = `# ${this.currentRoom} - найдено: ${count} по "${term}"`;
        } else {
            roomTitle.textContent = `# ${this.currentRoom} - ничего не найдено по "${term}"`;
        }
    }

    clearSearch() {
        const searchInput = document.getElementById('search-input');
        const clearBtn = document.getElementById('clear-search-btn');
        const roomTitle = document.getElementById('current-room');
        
        searchInput.value = '';
        clearBtn.classList.add('hidden');
        roomTitle.textContent = `# ${this.currentRoom}`;
        
        // Убираем подсветку
        document.querySelectorAll('.search-highlight').forEach(message => {
            message.classList.remove('search-highlight');
        });
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Проверяем размер файла (максимум 10MB)
        if (file.size > 10 * 1024 * 1024) {
            alert('Файл слишком большой. Максимальный размер: 10MB');
            return;
        }

        this.showFilePreview(file);
    }

    showFilePreview(file) {
        const preview = document.getElementById('file-preview');
        preview.innerHTML = '';

        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';

        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                fileItem.innerHTML = `
                    <div class="file-info">
                        <img src="${e.target.result}" alt="Preview" class="file-image-preview">
                        <div class="file-details">
                            <span class="file-name">${file.name}</span>
                            <span class="file-size">${this.formatFileSize(file.size)}</span>
                        </div>
                        <button class="btn-remove-file" title="Удалить файл">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
                // Добавляем обработчик только после установки innerHTML
                fileItem.querySelector('.btn-remove-file').addEventListener('click', () => {
                    this.removeFilePreview();
                });
            };
            reader.readAsDataURL(file);
        } else {
            fileItem.innerHTML = `
                <div class="file-info">
                    <div class="file-icon">
                        <i class="fas fa-file"></i>
                    </div>
                    <div class="file-details">
                        <span class="file-name">${file.name}</span>
                        <span class="file-size">${this.formatFileSize(file.size)}</span>
                    </div>
                    <button class="btn-remove-file" title="Удалить файл">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            fileItem.querySelector('.btn-remove-file').addEventListener('click', () => {
                this.removeFilePreview();
            });
        }

        preview.appendChild(fileItem);
        preview.classList.remove('hidden');
    }

    removeFilePreview() {
        const preview = document.getElementById('file-preview');
        const fileInput = document.getElementById('file-input');
        
        preview.classList.add('hidden');
        preview.innerHTML = '';
        fileInput.value = '';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async sendFile(file) {
        if (!this.currentRoom) return;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('room', this.currentRoom);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (result.success) {
                // Если это картинка, не добавляем текст, только файл
                const isImage = file.type && file.type.startsWith('image/');
                this.socket.emit('send_message', {
                    room: this.currentRoom,
                    message: isImage ? '' : `📎 Файл: ${file.name}`,
                    file: {
                        name: file.name,
                        size: file.size,
                        type: file.type,
                        url: result.url
                    }
                });
                this.removeFilePreview();
            } else {
                alert('Ошибка загрузки файла: ' + result.error);
            }
        } catch (error) {
            alert('Ошибка загрузки файла');
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    new OlegMessenger();
});


// Utility to read cookie
function getCookie(name){ const v = document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)'); return v ? v.pop() : ''; }

// Wrap window.fetch to attach CSRF token
const _origFetch = window.fetch.bind(window);
window.fetch = (input, init={}) => {
    init = init || {};
    const method = (init.method || 'GET').toUpperCase();
    if (['POST','PUT','PATCH','DELETE'].includes(method)) {
        init.headers = init.headers || {};
        if (init.headers instanceof Headers) {
            init.headers.set('X-CSRF-Token', getCookie('X-CSRF-Token') || '');
        } else {
            init.headers['X-CSRF-Token'] = getCookie('X-CSRF-Token') || '';
        }
    }
    return _origFetch(input, init);
};

// Подключение к WebSocket через Socket.IO
const socket = io();

// Слушаем событие "notification"
socket.on('notification', function(data) {
    showNotification(data.message);
});

// Функция для показа уведомления (toast)
function showNotification(message) {
    let notif = document.createElement('div');
    notif.className = 'toast-notification';
    notif.innerText = message;
    document.body.appendChild(notif);
    setTimeout(() => {
        notif.remove();
    }, 3000);
}

class OlegMessenger {
    constructor() {
        this.socket = null;
        this.currentUser = null;
        this.currentRoom = null;
        this.currentGuildId = null;
        this.currentChannelId = null;
        this.currentChannelName = null;
        this.typingUsers = new Set();
        this.typingTimeout = null;
        this.isPageVisible = true;
        this.friendsState = { friends: [], incoming: [], outgoing: [] };
        this.initializeEventListeners();
        this.initializeTheme();
        this.initializeNotifications();
        this.applyPrefs();
    }

    initializeEventListeners() {
        document.getElementById('login-btn').addEventListener('click', () => this.login());
        document.getElementById('register-btn').addEventListener('click', () => this.register());
        document.getElementById('logout-btn').addEventListener('click', () => this.logout());
        document.getElementById('theme-toggle-btn').addEventListener('click', () => this.toggleTheme());
        
        const openProfileBtn = document.getElementById('open-profile-btn');
        const closeProfileBtn = document.getElementById('close-profile-btn');
        const uploadAvatarBtn = document.getElementById('upload-avatar-btn');
        const avatarInput = document.getElementById('avatar-input');
        const saveProfileBtn = document.getElementById('save-profile-btn');
        if (openProfileBtn) openProfileBtn.addEventListener('click', () => this.openProfile());
        if (closeProfileBtn) closeProfileBtn.addEventListener('click', () => this.closeProfile());
        if (uploadAvatarBtn) uploadAvatarBtn.addEventListener('click', () => avatarInput.click());
        if (avatarInput) avatarInput.addEventListener('change', (e) => this.uploadAvatar(e));
        if (saveProfileBtn) saveProfileBtn.addEventListener('click', () => this.saveProfile());
        
        // Friends
        document.getElementById('friend-search-btn').addEventListener('click', () => this.searchUsers());
        document.getElementById('friend-search-input').addEventListener('keypress', (e) => { if (e.key === 'Enter') this.searchUsers(); });
        
        // Guilds/Channels
        const addGuildBtn = document.getElementById('add-guild-btn');
        if (addGuildBtn) addGuildBtn.addEventListener('click', () => this.createGuild());
        const addChannelBtn = document.getElementById('add-channel-btn');
        if (addChannelBtn) addChannelBtn.addEventListener('click', () => this.createChannel());
        
        // Chat
        document.getElementById('send-btn').addEventListener('click', () => this.sendMessage());
        document.getElementById('message-input').addEventListener('keypress', (e) => { if (e.key === 'Enter') this.sendMessage(); });
        document.getElementById('message-input').addEventListener('input', () => this.handleTyping());
        
        document.getElementById('emoji-btn').addEventListener('click', () => this.toggleEmojiPicker());
        document.addEventListener('click', (e) => { if (!e.target.closest('#emoji-picker') && !e.target.closest('#emoji-btn')) this.hideEmojiPicker(); });

        document.addEventListener('visibilitychange', () => { this.isPageVisible = !document.hidden; if (this.isPageVisible) this.clearNotifications(); });

        document.getElementById('search-btn').addEventListener('click', () => this.searchMessages());
        document.getElementById('search-input').addEventListener('keypress', (e) => { if (e.key === 'Enter') this.searchMessages(); });
        document.getElementById('clear-search-btn').addEventListener('click', () => this.clearSearch());
        
        document.getElementById('file-btn').addEventListener('click', () => { document.getElementById('file-input').click(); });
        document.getElementById('file-input').addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Drag & Drop
        this.setupDragAndDrop();
        
        // Infinite scroll
        this.setupInfiniteScroll();
        
        // Эмодзи, стикеры, опросы
        document.getElementById('sticker-btn').addEventListener('click', () => this.toggleStickerPanel());
        document.getElementById('close-sticker-btn').addEventListener('click', () => this.hideStickerPanel());
        document.getElementById('poll-btn').addEventListener('click', () => this.showPollModal());
        document.getElementById('close-poll-modal').addEventListener('click', () => this.hidePollModal());
        document.getElementById('cancel-poll').addEventListener('click', () => this.hidePollModal());
        document.getElementById('add-poll-option').addEventListener('click', () => this.addPollOption());
        document.getElementById('create-poll').addEventListener('click', () => this.createPoll());

        // Tabs and invites wiring additions inside initializeEventListeners
        const tabChannels = document.getElementById('tab-channels');
        const tabFriends = document.getElementById('tab-friends');
        if (tabChannels && tabFriends) {
            tabChannels.addEventListener('click', () => this.switchTab('channels'));
            tabFriends.addEventListener('click', () => this.switchTab('friends'));
        }
        const createInviteBtn = document.getElementById('create-invite-btn');
        if (createInviteBtn) createInviteBtn.addEventListener('click', () => this.createInvite());
        const joinInviteBtn = document.getElementById('join-invite-btn');
        if (joinInviteBtn) joinInviteBtn.addEventListener('click', () => this.joinInvite());

        // Settings wiring in initializeEventListeners
        const openSettingsBtn = document.getElementById('open-settings-btn');
        if (openSettingsBtn) openSettingsBtn.addEventListener('click', () => this.openSettings());
        const closeSettingsBtn = document.getElementById('close-settings-btn');
        if (closeSettingsBtn) closeSettingsBtn.addEventListener('click', () => this.closeSettings());

        // Add in initializeEventListeners: global hotkeys
        document.addEventListener('keydown', (e) => this.handleGlobalHotkeys(e));
    }

    getCsrfToken() {
        return getCookie('X-CSRF-Token') || '';
    }

    async login() {
        const username = document.getElementById('username-input').value.trim();
        const password = document.getElementById('password-input').value;
        if (!username || !password) { this.showError('Введите имя пользователя и пароль'); return; }
        try {
            const response = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
            const data = await response.json();
            if (data.success) { this.currentUser = data; this.showChatScreen(); this.initializeSocket(); }
            else { this.showError(data.error); }
        } catch { this.showError('Ошибка подключения к серверу'); }
    }

    async register() {
        const username = document.getElementById('username-input').value.trim();
        const password = document.getElementById('password-input').value;
        if (!username || !password) { this.showError('Введите имя пользователя и пароль'); return; }
        try {
            const response = await fetch('/api/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
            const data = await response.json();
            if (data.success) { this.currentUser = data; this.showChatScreen(); this.initializeSocket(); }
            else { this.showError(data.error); }
        } catch { this.showError('Ошибка подключения к серверу'); }
    }

    showChatScreen() {
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('chat-screen').classList.remove('hidden');
        document.getElementById('current-username').textContent = this.currentUser.username;
        this.loadUsers();
        this.refreshFriends();
        this.loadGuilds();
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

    showError(message) { const e = document.getElementById('login-error'); e.textContent = message; setTimeout(()=>{ e.textContent=''; },5000); }

    openProfile() { const modal = document.getElementById('profile-modal'); modal.classList.remove('hidden'); this.fetchProfile(); }
    closeProfile() { const modal = document.getElementById('profile-modal'); modal.classList.add('hidden'); }
    async fetchProfile(){ try{ const r = await fetch('/api/profile'); if(!r.ok) return; const p = await r.json(); document.getElementById('profile-avatar').src = p.avatar_url || ''; document.getElementById('status-input').value = p.status_text || ''; document.getElementById('bio-input').value = p.bio || ''; }catch{} }
    async saveProfile(){ const status = document.getElementById('status-input').value.trim(); const bio = document.getElementById('bio-input').value.trim(); try{ const r = await fetch('/api/profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ status_text: status, bio })}); const d = await r.json(); if(d.success){ this.closeProfile(); } }catch{ alert('Не удалось сохранить профиль'); } }
    async uploadAvatar(e){ const file = e.target.files[0]; if(!file) return; if(!file.type.startsWith('image/')) return alert('Выберите файл изображения'); if(file.size>5*1024*1024) return alert('Аватар слишком большой (макс 5MB)'); const form = new FormData(); form.append('avatar', file); try{ const r=await fetch('/api/upload_avatar',{method:'POST',body:form}); const d=await r.json(); if(d.success){ document.getElementById('profile-avatar').src = d.avatar_url; } else alert('Ошибка загрузки аватара'); }catch{ alert('Ошибка загрузки аватара'); } }

    initializeSocket() {
        this.socket = io();
        this.socket.on('connect', () => {});
        this.socket.on('disconnect', () => {});
        this.socket.on('new_message', (data) => { this.addMessage(data); if (data.username !== this.currentUser.username && (!this.isPageVisible || data.room !== this.currentRoom)) { this.showNotification(data); } if (data.username !== this.currentUser.username) { this.playNotifyBeep(); } });
        this.socket.on('user_status', () => { this.loadUsers(); });
        this.socket.on('room_joined', () => { this.updateRoomUsers(); });
        this.socket.on('room_left', () => { this.updateRoomUsers(); });
        this.socket.on('messages_history', (messages) => { this.loadMessages(messages); });
        this.socket.on('user_typing', (data) => { this.updateTypingIndicator(data); });
        this.socket.on('message_edited', (data) => { this.updateMessage(data); });
        this.socket.on('message_deleted', (data) => { this.removeMessage(data.message_id); });
        this.socket.on('reaction_updated', (data) => { this.updateReactions(data); });
        this.socket.on('friends_update', () => { this.refreshFriends(); });
        this.socket.on('user_profile_updated', () => { this.loadUsers(); this.refreshFriends(); });
        this.socket.on('rooms_updated', () => { /* legacy rooms */ });
        this.socket.on('guilds_updated', () => { this.loadGuilds(); });
        this.socket.on('channels_updated', (data) => { if (data.guild_id === this.currentGuildId) this.loadChannels(); else this.loadGuilds(); });
        this.socket.on('channel_settings_updated', (data) => { if (data.guild_id === this.currentGuildId) this.loadChannels(); });
        this.socket.on('permission_error', (data) => {
            if (data?.reason === 'read_only') {
                this.setSendEnabled(false);
                alert('Канал в режиме только чтение');
            }
        });
        this.socket.on('message_pinned', (data) => { this.applyPinned(data); });
        this.socket.on('thread_created', (data) => {
            if (data.guild_id === this.currentGuildId && data.channel_id === this.currentChannelId) this.loadThreads();
        });
    }

    setSendEnabled(enabled) {
        document.getElementById('message-input').disabled = !enabled;
        document.getElementById('send-btn').disabled = !enabled;
    }

    // Guilds/Channels
    async loadGuilds() {
        try {
            const res = await fetch('/api/guilds');
            const guilds = await res.json();
            const list = document.getElementById('guilds-list');
            list.innerHTML = '';
            guilds.forEach(g => {
                const btn = document.createElement('button');
                btn.className = 'server-item';
                btn.textContent = g.name[0]?.toUpperCase() || 'S';
                btn.title = g.name;
                btn.addEventListener('click', () => this.selectGuild(g.id, g.name, btn));
                list.appendChild(btn);
            });
            if (!this.currentGuildId && guilds.length) this.selectGuild(guilds[0].id, guilds[0].name, list.firstChild);
        } catch {}
    }

    async selectGuild(gid, name, buttonEl) {
        this.currentGuildId = gid;
        document.getElementById('current-guild-name').textContent = name;
        document.querySelectorAll('.server-item').forEach(b => b.classList.remove('active'));
        if (buttonEl) buttonEl.classList.add('active');
        await this.loadChannels();
    }

    async loadChannels() {
        if (!this.currentGuildId) return;
        try {
            const res = await fetch(`/api/guilds/${this.currentGuildId}/channels`);
            const channels = await res.json();
            const list = document.getElementById('channels-list');
            list.innerHTML = '';
            channels.forEach(c => {
                const item = document.createElement('div');
                item.className = 'channel-item';
                item.textContent = `# ${c.name}`;
                item.addEventListener('click', () => this.selectChannel(c.id, c.name, item, c.read_only));
                list.appendChild(item);
            });
            if (!this.currentChannelId && channels.length) this.selectChannel(channels[0].id, channels[0].name, list.firstChild, channels[0].read_only);
            await this.loadThreads();
            this.channelsMeta = channels.reduce((acc, c) => (acc[c.id]=c, acc), {});
        } catch {}
    }

    async createGuild() {
        const name = prompt('Имя сервера:');
        if (!name) return;
        try { await fetch('/api/guilds', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) }); this.loadGuilds(); }
        catch {}
    }

    async createChannel() {
        if (!this.currentGuildId) return alert('Сначала выберите сервер');
        const name = prompt('Имя канала:');
        if (!name) return;
        try { await fetch(`/api/guilds/${this.currentGuildId}/channels`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) }); this.loadChannels(); }
        catch {}
    }

    async selectChannel(cid, name, el, readOnlyFlag) {
        this.currentChannelId = cid;
        this.currentChannelName = name;
        document.getElementById('current-room').textContent = `# ${name}`;
        document.querySelectorAll('.channel-item').forEach(x => x.classList.remove('active'));
        if (el) el.classList.add('active');
        const room = `g:${this.currentGuildId}:c:${cid}`;
        this.joinRoom(room);
        this.socket.emit('get_messages', { room });
        this.setSendEnabled(true);
        // If channel is read-only and user not owner, disable send controls
        const meta = readOnlyFlag !== undefined ? { read_only: readOnlyFlag } : (this.channelsMeta?.[cid] || {});
        const isOwner = false; // client doesn't know owner; allow server enforcement. For UX, disable if read_only.
        if (meta.read_only && !isOwner) this.setSendEnabled(false);
        this.loadThreads();
        document.getElementById('search-input').disabled = false;
        document.getElementById('search-btn').disabled = false;
    }

    // Friends logic (unchanged API)
    async refreshFriends() { try { const res = await fetch('/api/friends/status'); if (!res.ok) return; this.friendsState = await res.json(); this.renderFriendsUI(); } catch {} }
    renderFriendsUI() {
        const inList = document.getElementById('friend-requests-in');
        const outList = document.getElementById('friend-requests-out');
        const friendsList = document.getElementById('friends-list');
        inList.innerHTML = ''; outList.innerHTML = ''; friendsList.innerHTML = '';
        this.friendsState.incoming.forEach(u => { const d = document.createElement('div'); d.className = 'item'; d.innerHTML = `<div class="left"><div class="user-status"></div><span>${u}</span></div><div class="right"><button class="btn-accept">Принять</button><button class="btn-decline">Отклонить</button></div>`; d.querySelector('.btn-accept').addEventListener('click', () => this.acceptFriend(u)); d.querySelector('.btn-decline').addEventListener('click', () => this.declineFriend(u)); inList.appendChild(d); });
        this.friendsState.outgoing.forEach(u => { const d = document.createElement('div'); d.className = 'item'; d.innerHTML = `<div class="left"><div class="user-status"></div><span>${u}</span></div><div class="right"><button class="btn-cancel">Отменить</button></div>`; d.querySelector('.btn-cancel').addEventListener('click', () => this.cancelFriend(u)); outList.appendChild(d); });
        this.friendsState.friends.forEach(u => { const d = document.createElement('div'); d.className = 'item'; d.innerHTML = `<div class="left"><div class="user-status"></div><span>${u}</span></div><div class="right"><button class="btn-open">Открыть ЛС</button><button class="btn-decline">Убрать из друзей</button></div>`; d.querySelector('.btn-open').addEventListener('click', () => this.openDM(u)); d.querySelector('.btn-decline').addEventListener('click', () => this.removeFriend(u)); friendsList.appendChild(d); });
    }

    async searchUsers() { const q = document.getElementById('friend-search-input').value.trim(); const resDiv = document.getElementById('friend-search-results'); resDiv.innerHTML=''; if (!q) return; try { const res = await fetch(`/api/user_search?q=${encodeURIComponent(q)}`); const list = await res.json(); list.forEach(({username, avatar_url}) => { if (username===this.currentUser.username) return; const d=document.createElement('div'); d.className='item'; d.innerHTML = `<div class="left">${avatar_url?`<img class='user-avatar' src='${avatar_url}'>`:'<div class="user-status"></div>'}<span>${username}</span></div><div class="right"><button class="btn-add">Добавить</button></div>`; d.querySelector('.btn-add').addEventListener('click', ()=> this.sendFriendRequest(username)); resDiv.appendChild(d); }); } catch {} }
    async sendFriendRequest(username){ 
        try{ 
            const csrfToken = getCookie('X-CSRF-Token');
            console.log('CSRF Token:', csrfToken);
            const res = await fetch('/api/friends/request',{
                method:'POST',
                headers:{
                    'Content-Type':'application/json',
                    'X-CSRF-Token': csrfToken
                },
                body:JSON.stringify({to:username})
            }); 
            if(!res.ok){ 
                const err = await res.json(); 
                console.error('Friend request error:', err);
                alert(err.error || 'Ошибка отправки заявки'); 
                return; 
            } 
            this.refreshFriends(); 
            this.searchUsers(); 
        }catch(e){ 
            console.error('Friend request exception:', e);
            alert('Ошибка отправки заявки'); 
        } 
    }
    async cancelFriend(username){ try{ await fetch('/api/friends/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:username})}); this.refreshFriends(); this.searchUsers(); }catch{}}
    async acceptFriend(username){ try{ await fetch('/api/friends/accept',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:username})}); this.refreshFriends(); }catch{}}
    async declineFriend(username){ try{ await fetch('/api/friends/decline',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:username})}); this.refreshFriends(); }catch{}}
    async removeFriend(username){ try{ await fetch('/api/friends/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:username})}); this.refreshFriends(); }catch{}}

    openDM(otherUsername) {
        if (!this.friendsState.friends.includes(otherUsername)) { alert('Можно писать только друзьям. Добавьте пользователя в друзья.'); return; }
        const self = this.currentUser.username; 
        const [a,b] = [self, otherUsername].sort((x,y)=>x.localeCompare(y)); 
        const dmRoom = `dm:${a}:${b}`; 
        this.joinRoom(dmRoom); 
        document.getElementById('current-room').textContent = `ЛС с ${otherUsername}`; 
        // Убираем дублирующий вызов get_messages, так как он уже есть в joinRoom
        document.getElementById('message-input').disabled = false; 
        document.getElementById('send-btn').disabled = false; 
    }

    async loadUsers() { try { const r = await fetch('/api/users'); const u = await r.json(); this.displayUsers(u); } catch (e) { console.error('Ошибка загрузки пользователей:', e); } }
    displayUsers(users) { /* users panel hidden in new layout, keep for profile badge refresh */ }

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
        
        const isDM = String(roomName).startsWith('dm:');
        document.getElementById('current-room').textContent = isDM ? `Личные сообщения` : `# ${roomName}`;
        document.getElementById('message-input').disabled = false;
        document.getElementById('send-btn').disabled = false;
        document.getElementById('search-input').disabled = false;
        document.getElementById('search-btn').disabled = false;
        
        document.querySelectorAll('.room-item').forEach(item => {
            item.classList.remove('active');
            if (item.textContent.trim() === `# ${roomName}`) {
                item.classList.add('active');
            }
        });
        
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
            this.sendFile(file);
        }
        
        if (message) {
            this.socket.emit('send_message', {
                room: this.currentRoom,
                message: message
            });
        }
        
        messageInput.value = '';
        focusInput();
        scrollToBottom();
    }

    addMessage(data) {
        const messagesList = document.getElementById('messages-list');
        const messageElement = document.createElement('div');
        messageElement.className = `message ${data.username === this.currentUser.username ? 'own' : 'other'} ${data.pinned ? 'pinned' : ''}`;
        messageElement.dataset.messageId = data.id;

        const timestamp = new Date(data.timestamp).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        const editedIndicator = data.edited ? '<span class="edited-indicator">(изменено)</span>' : '';
        const pinBadge = data.pinned ? '<span class="pin-badge">Закреплено</span>' : '';
        const threadBadge = data.thread_id ? `<span class="pin-badge" title="Нить" data-thread-id="${data.thread_id}">Нить</span>` : '';
        const header = `<div class="message-header"><span class="message-username">${data.username}</span><span class="message-time">${timestamp}</span>${editedIndicator}${pinBadge}${threadBadge}</div>`;

        // Click on thread badge to open
        if (data.thread_id) {
            setTimeout(() => {
                const badge = messageElement.querySelector('.pin-badge[data-thread-id]');
                if (badge) {
                    badge.addEventListener('click', () => this.openThread(data.thread_id));
                }
            }, 0);
        }

        let fileContent = '';
        let messageContent = this.escapeHtml(data.message || '');
        if (data.file) {
            const fname = this.escapeHtml(data.file.name || 'файл');
            const furl = data.file.url;
            const ftype = data.file.type || '';
            if (ftype.startsWith('image/')) {
                fileContent = `<div class="message-file"><img src="${furl}" alt="${fname}" class="message-image"></div>`;
                if (!messageContent) messageContent = '';
            } else {
                const size = data.file.size ? ` (${this.formatFileSize(data.file.size)})` : '';
                fileContent = `<div class="message-file"><a href="${furl}" target="_blank" class="file-link"><i class="fas fa-file"></i> ${fname}${size}</a></div>`;
            }
        }
        const avatar = `<div class="avatar">${data.username[0].toUpperCase()}</div>`;
        const contentHTML = messageContent ? `<div class="message-content">${messageContent}</div>` : '';
        const reactionsHTML = this.renderReactions(data.reactions || {});
        const contentBlock = `<div class="message-content-block">${header}${contentHTML}${fileContent}${reactionsHTML}</div>`;
        messageElement.innerHTML = `${avatar}${contentBlock}`;

        // Context menu
        messageElement.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.showMessageContextMenu(e.pageX, e.pageY, data);
        });

        const img = messageElement.querySelector('.message-image');
        if (img) { img.addEventListener('click', () => { window.open(img.src, '_blank'); }); }
        const reactionAddBtn = messageElement.querySelector('.add-reaction-btn');
        if (reactionAddBtn) reactionAddBtn.addEventListener('click', () => { const emoji = prompt('Введите эмодзи для реакции (например, 😀):'); if (emoji) this.addReaction(data.id, emoji); });
        messageElement.querySelectorAll('.reaction').forEach(el => { el.addEventListener('click', () => { const emoji = el.dataset.emoji; if (el.classList.contains('reacted')) this.removeReaction(data.id, emoji); else this.addReaction(data.id, emoji); }); });
        messagesList.appendChild(messageElement);
        messagesList.scrollTop = messagesList.scrollHeight;
        scrollToBottom();
        focusInput();
    }

    showMessageContextMenu(x, y, messageData) {
        this.removeContextMenu();
        const menu = document.createElement('div');
        menu.className = 'context-menu';
        const isPinned = !!messageData.pinned;
        const hasThread = !!messageData.thread_id;
        menu.innerHTML = `
            <div class="item" data-action="copy-link">Копировать ссылку</div>
            <div class="item" data-action="${isPinned ? 'unpin' : 'pin'}">${isPinned ? 'Открепить' : 'Закрепить'}</div>
            <div class="item" data-action="${hasThread ? 'open-thread' : 'create-thread'}">${hasThread ? 'Открыть нить' : 'Создать нить'}</div>
        `;
        document.body.appendChild(menu);
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
        const handle = (e) => {
            const action = e.target?.dataset?.action;
            if (action === 'copy-link') {
                const url = `${location.origin}${location.pathname}?room=${encodeURIComponent(this.currentRoom)}&mid=${messageData.id}`;
                navigator.clipboard?.writeText(url);
            } else if (action === 'pin') {
                this.socket.emit('pin_message', { room: this.currentRoom, message_id: messageData.id });
            } else if (action === 'unpin') {
                this.socket.emit('unpin_message', { room: this.currentRoom, message_id: messageData.id });
            } else if (action === 'create-thread') {
                const title = prompt('Название нити:', 'Обсуждение');
                if (title) this.createThread(title, messageData.id);
            } else if (action === 'open-thread') {
                this.openThread(messageData.thread_id);
            }
            this.removeContextMenu();
        };
        menu.addEventListener('click', handle);
        setTimeout(() => { document.addEventListener('click', () => this.removeContextMenu(), { once: true }); }, 0);
    }

    removeContextMenu() { document.querySelectorAll('.context-menu').forEach(m => m.remove()); }

    renderReactions(reactions) {
        const entries = Object.entries(reactions);
        const pills = entries.map(([emoji, users]) => {
            const count = users.length;
            const reacted = users.includes(this.currentUser?.username) ? 'reacted' : '';
            return `<span class="reaction ${reacted}" data-emoji="${emoji}">${emoji} ${count}</span>`;
        }).join('');
        return `<div class="reactions-row">${pills}<button class="add-reaction-btn" title="Добавить реакцию">+</button></div>`;
    }

    updateReactions({ message_id, reactions }) {
        const messageElement = document.querySelector(`[data-message-id="${message_id}"]`);
        if (!messageElement) return;
        const block = messageElement.querySelector('.message-content-block');
        let row = block.querySelector('.reactions-row');
        if (row) row.remove();
        block.insertAdjacentHTML('beforeend', this.renderReactions(reactions));
        const reactionAddBtn = block.querySelector('.add-reaction-btn');
        if (reactionAddBtn) {
            reactionAddBtn.addEventListener('click', () => {
                const emoji = prompt('Введите эмодзи для реакции (например, 😀):');
                if (emoji) this.addReaction(message_id, emoji);
            });
        }
        block.querySelectorAll('.reaction').forEach(el => {
            el.addEventListener('click', () => {
                const emoji = el.dataset.emoji;
                if (el.classList.contains('reacted')) {
                    this.removeReaction(message_id, emoji);
                } else {
                    this.addReaction(message_id, emoji);
                }
            });
        });
    }

    addReaction(messageId, emoji) {
        if (!this.currentRoom) return;
        this.socket.emit('add_reaction', { room: this.currentRoom, message_id: messageId, emoji });
    }

    removeReaction(messageId, emoji) {
        if (!this.currentRoom) return;
        this.socket.emit('remove_reaction', { room: this.currentRoom, message_id: messageId, emoji });
    }

    loadMessages(messages) {
        const messagesList = document.getElementById('messages-list');
        messagesList.innerHTML = '';
        messages.forEach(message => {
            this.addMessage(message);
        });
    }

    async loadMessagesWithPagination(page = 1) {
        if (!this.currentChannel) return;
        
        try {
            // Показываем skeleton loading для первой загрузки
            if (page === 1) {
                this.showSkeletonLoading();
            }
            
            const response = await fetch(`/api/channels/${this.currentChannel}/messages?page=${page}&limit=50`);
            const data = await response.json();
            
            if (page === 1) {
                this.hideSkeletonLoading();
                this.displayMessages(data.messages);
            } else {
                this.prependMessages(data.messages);
            }
            
            this.currentPage = page;
            this.totalPages = data.pagination.pages;
            this.hasMoreMessages = page < data.pagination.pages;
            
        } catch (error) {
            console.error('Ошибка загрузки сообщений:', error);
            this.hideSkeletonLoading();
        }
    }

    prependMessages(messages) {
        const messagesList = document.getElementById('messages-list');
        const fragment = document.createDocumentFragment();
        
        messages.reverse().forEach(message => {
            const messageElement = this.createMessageElement(message);
            fragment.appendChild(messageElement);
        });
        
        messagesList.insertBefore(fragment, messagesList.firstChild);
    }

    setupInfiniteScroll() {
        const messagesList = document.getElementById('messages-list');
        if (!messagesList) return;
        
        messagesList.addEventListener('scroll', () => {
            if (messagesList.scrollTop === 0 && this.hasMoreMessages) {
                this.loadMessagesWithPagination(this.currentPage + 1);
            }
        });
    }

    // Виртуализация для больших списков
    setupVirtualization() {
        const messagesList = document.getElementById('messages-list');
        if (!messagesList) return;
        
        const ITEM_HEIGHT = 60; // Примерная высота сообщения
        const VISIBLE_ITEMS = Math.ceil(messagesList.clientHeight / ITEM_HEIGHT) + 5; // +5 для буфера
        
        let startIndex = 0;
        let endIndex = VISIBLE_ITEMS;
        
        const virtualize = () => {
            const scrollTop = messagesList.scrollTop;
            const newStartIndex = Math.floor(scrollTop / ITEM_HEIGHT);
            const newEndIndex = Math.min(newStartIndex + VISIBLE_ITEMS, this.allMessages.length);
            
            if (newStartIndex !== startIndex || newEndIndex !== endIndex) {
                startIndex = newStartIndex;
                endIndex = newEndIndex;
                this.renderVisibleMessages();
            }
        };
        
        messagesList.addEventListener('scroll', virtualize);
    }

    renderVisibleMessages() {
        const messagesList = document.getElementById('messages-list');
        const fragment = document.createDocumentFragment();
        
        // Создаем виртуальный контейнер
        const virtualContainer = document.createElement('div');
        virtualContainer.style.height = `${this.allMessages.length * 60}px`;
        virtualContainer.style.position = 'relative';
        
        // Рендерим только видимые сообщения
        for (let i = this.startIndex; i < this.endIndex; i++) {
            if (this.allMessages[i]) {
                const messageElement = this.createMessageElement(this.allMessages[i]);
                messageElement.style.position = 'absolute';
                messageElement.style.top = `${i * 60}px`;
                messageElement.style.height = '60px';
                virtualContainer.appendChild(messageElement);
            }
        }
        
        messagesList.innerHTML = '';
        messagesList.appendChild(virtualContainer);
    }

    updateRoomUsers() {
        document.getElementById('room-users-count').textContent = 'Пользователи обновляются...';
    }

    logout() {
        this.showLoginScreen();
    }

    handleTyping() {
        if (!this.currentRoom) return;
        this.socket.emit('typing_start', { room: this.currentRoom });
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }
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
        if (typingIndicator) {
            typingIndicator.remove();
        }
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
            if (contentElement) contentElement.textContent = data.new_content;
            const editedAt = new Date(data.edited_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
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
        try {
            const prefs = this.loadPrefs();
            // Включим звук по умолчанию, если пользователь ещё не выбирал
            if (prefs.notifySound === undefined) {
                prefs.notifySound = true;
                this.savePrefs(prefs);
            }
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
        } catch {}
    }

    showNotification(data) {
        if (!('Notification' in window)) {
            return;
        }
        if (Notification.permission !== 'granted') {
            return;
        }
        const bodyText = data.message && data.message.trim() ? data.message : (data.file ? `📎 ${data.file.name}` : 'Новое сообщение');
        const notification = new Notification(`Oleg Messenger`, {
            body: `${data.username}: ${bodyText}`,
            icon: '/static/favicon.ico',
            tag: `message-${data.room}`,
            requireInteraction: false
        });
        setTimeout(() => {
            notification.close();
        }, 5000);
        notification.onclick = () => {
            window.focus();
            if (data.room !== this.currentRoom) {
                this.joinRoom(data.room);
            }
            notification.close();
        };
    }

    clearNotifications() {
        if ('Notification' in window) {
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
            const contentNode = message.querySelector('.message-content');
            const content = contentNode ? contentNode.textContent.toLowerCase() : '';
            const username = message.querySelector('.message-header span').textContent.toLowerCase();
            if (content.includes(searchTerm.toLowerCase()) || username.includes(searchTerm.toLowerCase())) {
                message.classList.add('search-highlight');
                message.scrollIntoView({ behavior: 'smooth', block: 'center' });
                foundCount++;
            } else {
                message.classList.remove('search-highlight');
            }
        });
        this.showSearchResults(foundCount, searchTerm);
    }

    showSearchResults(count, term) {
        const clearBtn = document.getElementById('clear-search-btn');
        clearBtn.classList.remove('hidden');
        const roomTitle = document.getElementById('current-room');
        const titleName = this.currentChannelName || this.currentChannelId || this.currentRoom || '';
        if (count > 0) {
            roomTitle.textContent = `# ${titleName} - найдено: ${count} по "${term}"`;
        } else {
            roomTitle.textContent = `# ${titleName} - ничего не найдено по "${term}"`;
        }
    }

    clearSearch() {
        const searchInput = document.getElementById('search-input');
        const clearBtn = document.getElementById('clear-search-btn');
        const roomTitle = document.getElementById('current-room');
        searchInput.value = '';
        clearBtn.classList.add('hidden');
        const titleName = this.currentChannelName || this.currentChannelId || this.currentRoom || '';
        roomTitle.textContent = `# ${titleName}`;
        document.querySelectorAll('.search-highlight').forEach(message => { message.classList.remove('search-highlight'); });
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        const allowedExt = ['png','jpg','jpeg','gif','pdf','doc','docx','txt'];
        const ext = file.name.split('.').pop().toLowerCase();
        if (!allowedExt.includes(ext)) {
            alert('Недопустимый тип файла. Разрешены: ' + allowedExt.join(', '));
            return;
        }
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
        preview.style.display = 'block';
    }

    removeFilePreview() {
        const preview = document.getElementById('file-preview');
        const fileInput = document.getElementById('file-input');
        preview.classList.add('hidden');
        preview.innerHTML = '';
        fileInput.value = '';
        // Жёстко убираем из потока
        preview.style.display = 'none';
        preview.style.height = '';
        preview.style.margin = '';
        preview.style.padding = '';
        focusInput();
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async sendFile(file) {
        const allowedExt = ['png','jpg','jpeg','gif','pdf','doc','docx','txt'];
        const ext = file.name.split('.').pop().toLowerCase();
        if (!allowedExt.includes(ext)) {
            alert('Недопустимый тип файла. Разрешены: ' + allowedExt.join(', '));
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            alert('Файл слишком большой. Максимальный размер: 10MB');
            return;
        }
        if (!this.currentRoom) return;
        const formData = new FormData();
        formData.append('file', file);
        formData.append('room', this.currentRoom);
        try {
            const response = await fetch('/api/upload', { method: 'POST', body: formData });
            const result = await response.json();
            if (result.success) {
                const isImage = file.type && file.type.startsWith('image/');
                this.socket.emit('send_message', {
                    room: this.currentRoom,
                    message: isImage ? '' : `📎 Файл: ${file.name}`,
                    file: { name: file.name, size: file.size, type: file.type, url: result.url }
                });
                this.removeFilePreview();
                focusInput();
                scrollToBottom();
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

    setupDragAndDrop() {
        const messagesContainer = document.querySelector('.messages-container');
        const messageInputContainer = document.querySelector('.message-input-container');
        
        if (!messagesContainer || !messageInputContainer) return;
        
        // Обработчики для контейнера сообщений
        messagesContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
            messagesContainer.classList.add('drag-over');
        });
        
        messagesContainer.addEventListener('dragleave', (e) => {
            e.preventDefault();
            messagesContainer.classList.remove('drag-over');
        });
        
        messagesContainer.addEventListener('drop', (e) => {
            e.preventDefault();
            messagesContainer.classList.remove('drag-over');
            this.handleFileDrop(e);
        });
        
        // Обработчики для области ввода сообщений
        messageInputContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
            messageInputContainer.classList.add('drag-over');
        });
        
        messageInputContainer.addEventListener('dragleave', (e) => {
            e.preventDefault();
            messageInputContainer.classList.remove('drag-over');
        });
        
        messageInputContainer.addEventListener('drop', (e) => {
            e.preventDefault();
            messageInputContainer.classList.remove('drag-over');
            this.handleFileDrop(e);
        });
    }

    handleFileDrop(e) {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            this.handleFileSelect({ target: { files: [file] } });
        }
    }

    showSkeletonLoading() {
        const messagesList = document.getElementById('messages-list');
        if (!messagesList) return;
        
        // Показываем 3 skeleton-сообщения
        for (let i = 0; i < 3; i++) {
            const skeleton = document.createElement('div');
            skeleton.className = 'skeleton skeleton-message';
            skeleton.innerHTML = `
                <div style="display: flex; align-items: center; padding: 12px;">
                    <div class="skeleton skeleton-avatar"></div>
                    <div style="flex: 1;">
                        <div class="skeleton skeleton-text short"></div>
                        <div class="skeleton skeleton-text medium"></div>
                    </div>
                </div>
            `;
            messagesList.appendChild(skeleton);
        }
    }

    hideSkeletonLoading() {
        const messagesList = document.getElementById('messages-list');
        if (!messagesList) return;
        
        const skeletons = messagesList.querySelectorAll('.skeleton-message');
        skeletons.forEach(skeleton => skeleton.remove());
    }

    // Стикеры
    toggleStickerPanel() {
        const panel = document.getElementById('sticker-panel');
        if (panel.classList.contains('hidden')) {
            this.showStickerPanel();
        } else {
            this.hideStickerPanel();
        }
    }

    showStickerPanel() {
        const panel = document.getElementById('sticker-panel');
        panel.classList.remove('hidden');
        this.loadStickers();
    }

    hideStickerPanel() {
        const panel = document.getElementById('sticker-panel');
        panel.classList.add('hidden');
    }

    async loadStickers() {
        if (!this.currentGuild) return;
        
        try {
            const response = await fetch(`/api/guilds/${this.currentGuild}/stickers`);
            const stickers = await response.json();
            
            const grid = document.getElementById('sticker-grid');
            grid.innerHTML = '';
            
            stickers.forEach(sticker => {
                const item = document.createElement('div');
                item.className = 'sticker-item';
                item.innerHTML = `<img src="/uploads/${sticker.file_path}" alt="${sticker.name}" title="${sticker.name}">`;
                item.addEventListener('click', () => this.sendSticker(sticker));
                grid.appendChild(item);
            });
        } catch (error) {
            console.error('Ошибка загрузки стикеров:', error);
        }
    }

    sendSticker(sticker) {
        if (!this.currentRoom) return;
        
        const message = `:sticker:${sticker.name}:`;
        this.sendMessage(message);
        this.hideStickerPanel();
    }

    // Опросы
    showPollModal() {
        const modal = document.getElementById('poll-modal');
        modal.classList.remove('hidden');
        
        // Сброс формы
        document.getElementById('poll-question').value = '';
        document.getElementById('allow-multiple-votes').checked = false;
        document.getElementById('poll-expires').value = '';
        
        const options = document.getElementById('poll-options');
        options.innerHTML = `
            <input type="text" class="poll-option" placeholder="Вариант 1" maxlength="100">
            <input type="text" class="poll-option" placeholder="Вариант 2" maxlength="100">
        `;
    }

    hidePollModal() {
        const modal = document.getElementById('poll-modal');
        modal.classList.add('hidden');
    }

    addPollOption() {
        const options = document.getElementById('poll-options');
        const optionCount = options.children.length;
        
        if (optionCount >= 10) {
            alert('Максимум 10 вариантов ответа');
            return;
        }
        
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'poll-option';
        input.placeholder = `Вариант ${optionCount + 1}`;
        input.maxLength = 100;
        options.appendChild(input);
    }

    async createPoll() {
        const question = document.getElementById('poll-question').value.trim();
        const allowMultiple = document.getElementById('allow-multiple-votes').checked;
        const expiresHours = document.getElementById('poll-expires').value;
        
        if (!question) {
            alert('Введите вопрос');
            return;
        }
        
        const optionInputs = document.querySelectorAll('.poll-option');
        const options = Array.from(optionInputs)
            .map(input => input.value.trim())
            .filter(value => value);
        
        if (options.length < 2) {
            alert('Минимум 2 варианта ответа');
            return;
        }
        
        try {
            // Сначала отправляем сообщение с опросом
            const message = `📊 **${question}**\n\n${options.map((opt, i) => `${i + 1}. ${opt}`).join('\n')}`;
            this.sendMessage(message);
            
            // Затем создаем опрос через API
            const response = await fetch(`/api/messages/${this.lastMessageId}/poll`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCsrfToken()
                },
                body: JSON.stringify({
                    question: question,
                    options: options,
                    allow_multiple: allowMultiple,
                    expires_hours: expiresHours ? parseInt(expiresHours) : null
                })
            });
            
            if (response.ok) {
                this.hidePollModal();
            } else {
                const error = await response.json();
                alert('Ошибка создания опроса: ' + error.error);
            }
        } catch (error) {
            console.error('Ошибка создания опроса:', error);
            alert('Ошибка создания опроса');
        }
    }

    async loadPoll(messageId) {
        try {
            const response = await fetch(`/api/messages/${messageId}/poll`);
            if (response.ok) {
                const poll = await response.json();
                this.renderPoll(poll, messageId);
            }
        } catch (error) {
            console.error('Ошибка загрузки опроса:', error);
        }
    }

    renderPoll(poll, messageId) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageElement) return;
        
        const pollContainer = document.createElement('div');
        pollContainer.className = 'poll-container';
        
        const totalVotes = poll.options.reduce((sum, opt) => sum + opt.votes, 0);
        
        pollContainer.innerHTML = `
            <div class="poll-question">${this.escapeHtml(poll.question)}</div>
            <div class="poll-options">
                ${poll.options.map(option => {
                    const percentage = totalVotes > 0 ? (option.votes / totalVotes) * 100 : 0;
                    const isVoted = poll.user_votes.includes(option.id);
                    
                    return `
                        <div class="poll-option-item ${isVoted ? 'voted' : ''}" data-option-id="${option.id}">
                            <div class="poll-option-text">${this.escapeHtml(option.text)}</div>
                            <div class="poll-option-votes">${option.votes}</div>
                            <div class="poll-progress">
                                <div class="poll-progress-bar" style="width: ${percentage}%"></div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
            <div class="poll-footer">
                <span>Всего голосов: ${totalVotes}</span>
                ${poll.expires_at ? `<span class="poll-expires">Истекает: ${new Date(poll.expires_at).toLocaleString()}</span>` : ''}
            </div>
        `;
        
        // Добавляем обработчики кликов
        pollContainer.querySelectorAll('.poll-option-item').forEach(item => {
            item.addEventListener('click', () => this.votePoll(poll.id, item.dataset.optionId));
        });
        
        messageElement.appendChild(pollContainer);
    }

    async votePoll(pollId, optionId) {
        try {
            const response = await fetch(`/api/polls/${pollId}/vote`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCsrfToken()
                },
                body: JSON.stringify({ option_id: optionId })
            });
            
            if (response.ok) {
                const updatedPoll = await response.json();
                // Обновляем отображение опроса
                const pollContainer = document.querySelector(`[data-message-id] .poll-container`);
                if (pollContainer) {
                    pollContainer.remove();
                    this.renderPoll(updatedPoll, this.lastMessageId);
                }
            } else {
                const error = await response.json();
                alert('Ошибка голосования: ' + error.error);
            }
        } catch (error) {
            console.error('Ошибка голосования:', error);
            alert('Ошибка голосования');
        }
    }

    applyPinned({ room, message_id, pinned }) {
        if (room !== this.currentRoom) return;
        const el = document.querySelector(`[data-message-id="${message_id}"]`);
        if (!el) return;
        el.classList.toggle('pinned', !!pinned);
        const header = el.querySelector('.message-header');
        if (!header) return;
        const existing = header.querySelector('.pin-badge');
        if (pinned && !existing) {
            const span = document.createElement('span');
            span.className = 'pin-badge';
            span.textContent = 'Закреплено';
            header.appendChild(span);
        } else if (!pinned && existing) {
            existing.remove();
        }
    }

    // New helpers
    switchTab(tab) {
        const tc = document.getElementById('tab-content-channels');
        const tf = document.getElementById('tab-content-friends');
        const bC = document.getElementById('tab-channels');
        const bF = document.getElementById('tab-friends');
        if (tab === 'channels') {
            tc.classList.remove('hidden');
            tf.classList.add('hidden');
            bC.classList.add('active');
            bF.classList.remove('active');
        } else {
            tc.classList.add('hidden');
            tf.classList.remove('hidden');
            bC.classList.remove('active');
            bF.classList.add('active');
        }
    }

    async createInvite() {
        if (!this.currentGuildId) return alert('Сначала выберите сервер');
        try {
            const r = await fetch(`/api/guilds/${this.currentGuildId}/invites`, { method: 'POST' });
            const d = await r.json();
            if (d.success) {
                const code = d.code;
                const text = `Инвайт-код: ${code}`;
                alert(text);
                navigator.clipboard?.writeText(code);
            } else alert(d.error || 'Не удалось создать инвайт');
        } catch { alert('Не удалось создать инвайт'); }
    }

    async joinInvite() {
        const code = document.getElementById('invite-code-input').value.trim();
        if (!code) return;
        try {
            const r = await fetch('/api/invites/join', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code }) });
            const d = await r.json();
            if (d.success) {
                this.loadGuilds();
                alert('Вы присоединились к серверу');
            } else alert(d.error || 'Неверный инвайт');
        } catch { alert('Не удалось присоединиться'); }
    }

    async loadThreads() {
        if (!this.currentGuildId || !this.currentChannelId) return;
        try {
            const r = await fetch(`/api/guilds/${this.currentGuildId}/channels/${this.currentChannelId}/threads`);
            const list = await r.json();
            const container = document.getElementById('channels-list');
            if (!container) return;
            // Append a simple divider and threads list
            const old = document.getElementById('threads-list');
            if (old) old.remove();
            const wrap = document.createElement('div');
            wrap.id = 'threads-list';
            wrap.style.marginTop = '8px';
            list.forEach(t => {
                const item = document.createElement('div');
                item.className = 'channel-item';
                item.textContent = `🧵 ${t.title}`;
                item.addEventListener('click', () => this.openThread(t.id));
                wrap.appendChild(item);
            });
            container.appendChild(wrap);
        } catch {}
    }

    createThread(title, parentMessageId) {
        if (!this.currentGuildId || !this.currentChannelId) return;
        this.socket.emit('create_thread', { guild_id: this.currentGuildId, channel_id: this.currentChannelId, title, parent_message_id: parentMessageId });
    }

    openThread(threadId) {
        const base = `g:${this.currentGuildId}:c:${this.currentChannelId}`;
        const threadRoom = `${base}:t:${threadId}`;
        this.joinRoom(threadRoom);
        this.socket.emit('get_messages', { room: threadRoom });
        document.getElementById('current-room').textContent = `🧵 ${threadId}`;
        this.setSendEnabled(true);
    }

    // Settings methods
    openSettings() {
        const modal = document.getElementById('settings-modal');
        // Prefill
        document.getElementById('st-status').value = document.getElementById('status-input')?.value || '';
        document.getElementById('st-bio').value = document.getElementById('bio-input')?.value || '';
        const prefs = this.loadPrefs();
        document.getElementById('st-theme').value = prefs.theme || (document.body.classList.contains('dark-theme') ? 'dark' : 'light');
        document.getElementById('st-compact').checked = !!prefs.compact;
        document.getElementById('st-notify-desktop').checked = !!prefs.notifyDesktop;
        document.getElementById('st-notify-sound').checked = !!prefs.notifySound;
        document.querySelectorAll('.settings-tab').forEach(btn => { btn.addEventListener('click', () => this.switchSettingsTab(btn.dataset.tab)); });
        const saveBtn = document.getElementById('st-save-profile');
        if (saveBtn) saveBtn.onclick = () => this.saveSettingsProfile();
        const delBtn = document.getElementById('st-delete-account');
        if (delBtn) delBtn.onclick = () => this.deleteAccount();
        const exportBtn = document.getElementById('st-export');
        if (exportBtn) exportBtn.onclick = () => this.exportData();
        const importBtn = document.getElementById('st-import');
        const importFile = document.getElementById('st-import-file');
        if (importBtn && importFile) {
            importBtn.onclick = () => importFile.click();
            importFile.onchange = () => this.importData(importFile.files[0]);
        }
        modal.classList.remove('hidden');
    }

    closeSettings() { document.getElementById('settings-modal').classList.add('hidden'); }

    switchSettingsTab(tab) {
        document.querySelectorAll('.settings-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
        document.querySelectorAll('.settings-panel').forEach(p => p.classList.toggle('hidden', p.dataset.panel !== tab));
    }

    loadPrefs() {
        try { return JSON.parse(localStorage.getItem('oleg-prefs') || '{}'); } catch { return {}; }
    }

    savePrefs(prefs) { localStorage.setItem('oleg-prefs', JSON.stringify(prefs)); }

    applyPrefs() {
        const prefs = this.loadPrefs();
        if (prefs.theme) { this.setTheme(prefs.theme); }
        document.body.classList.toggle('compact', !!prefs.compact);
        // Notifications: request permission if enabled
        if (prefs.notifyDesktop && 'Notification' in window && Notification.permission === 'default') Notification.requestPermission();
    }

    async saveSettingsProfile() {
        const status = document.getElementById('st-status').value.trim();
        const bio = document.getElementById('st-bio').value.trim();
        const theme = document.getElementById('st-theme').value;
        const compact = document.getElementById('st-compact').checked;
        const notifyDesktop = document.getElementById('st-notify-desktop').checked;
        const notifySound = document.getElementById('st-notify-sound').checked;
        // Save profile to backend
        try { await fetch('/api/profile', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ status_text: status, bio }) }); } catch {}
        // Save prefs locally
        const prefs = this.loadPrefs();
        Object.assign(prefs, { theme, compact, notifyDesktop, notifySound });
        this.savePrefs(prefs);
        this.applyPrefs();
        this.closeSettings();
    }

    async deleteAccount() {
        const password = prompt('Для подтверждения удаления введите пароль:');
        if (!password) return;
        try {
            const r = await fetch('/api/account/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }) });
            const d = await r.json();
            if (d.success) {
                alert('Аккаунт удалён');
                location.reload();
            } else {
                alert(d.error || 'Не удалось удалить аккаунт');
            }
        } catch { alert('Не удалось удалить аккаунт'); }
    }

    async exportData() {
        try {
            const r = await fetch('/api/admin/export');
            const blob = await r.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'oleg_messenger_export.json';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch { alert('Не удалось экспортировать данные'); }
    }

    async importData(file) {
        if (!file) return;
        try {
            const text = await file.text();
            const payload = JSON.parse(text);
            const r = await fetch('/api/admin/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const d = await r.json();
            if (d.success) {
                alert('Импорт выполнен');
                location.reload();
            } else {
                alert(d.error || 'Не удалось импортировать');
            }
        } catch { alert('Не удалось импортировать'); }
    }

    // Helpers for hotkeys
    handleGlobalHotkeys(e) {
        const isInput = ['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName);
        // Ctrl+K focus search
        if (e.ctrlKey && (e.key === 'k' || e.key === 'K')) {
            e.preventDefault();
            const si = document.getElementById('search-input');
            if (si && !si.disabled) { si.focus(); si.select(); }
            return;
        }
        // Ctrl+Enter send
        if (e.ctrlKey && e.key === 'Enter') {
            const mi = document.getElementById('message-input');
            if (mi && !mi.disabled) {
                e.preventDefault();
                this.sendMessage();
            }
            return;
        }
        // Alt+Up / Alt+Down switch channels when not typing in input (but allow from anywhere)
        if (e.altKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
            e.preventDefault();
            this.switchChannelOffset(e.key === 'ArrowUp' ? -1 : 1);
            return;
        }
        // Escape closes context menu
        if (e.key === 'Escape') this.removeContextMenu();
    }

    switchChannelOffset(offset) {
        const list = document.getElementById('channels-list');
        if (!list) return;
        const items = Array.from(list.querySelectorAll('.channel-item'));
        if (items.length === 0) return;
        const currentIndex = items.findIndex(el => el.classList.contains('active'));
        let nextIndex = currentIndex + offset;
        if (nextIndex < 0) nextIndex = items.length - 1;
        if (nextIndex >= items.length) nextIndex = 0;
        const nextEl = items[nextIndex];
        nextEl.click();
        nextEl.scrollIntoView({ block: 'nearest' });
    }

    // Notification sound
    playNotifyBeep() {
        try {
            const prefs = this.loadPrefs();
            if (!prefs.notifySound) return;
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const o = ctx.createOscillator();
            const g = ctx.createGain();
            o.type = 'sine';
            o.frequency.value = 880;
            o.connect(g);
            g.connect(ctx.destination);
            g.gain.setValueAtTime(0.0001, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.05, ctx.currentTime + 0.01);
            g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.2);
            o.start();
            o.stop(ctx.currentTime + 0.21);
        } catch {}
    }

    // Trigger sound for new messages not from self and visible conditions
    // (hooked in initializeSocket)
}

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => { new OlegMessenger(); });

// После отправки сообщения или фото:
function focusInput() {
    const input = document.getElementById('message-input');
    if (input) {
        input.focus();
    }
}
// Вызовите focusInput() после отправки сообщения/файла

function scrollToBottom() {
    const chat = document.getElementById('messages-list');
    if (chat) {
        chat.scrollTop = chat.scrollHeight;
    }
}
// Вызовите scrollToBottom() после добавления нового сообщения/файла


document.addEventListener('DOMContentLoaded', () => {
    const socket = io(); // Connect to Socket.IO server
    // --- DOM Elements ---
    const messageInput = document.getElementById('message-input');
    const recipientUsernameInput = document.getElementById('recipient-username-input'); // For DMs
    const sendButton = document.getElementById('send-button');
    const recordButton = document.getElementById('record-button');
    const stopRecordButton = document.getElementById('stop-record-button');
    const timerSpan = document.getElementById('timer');
    const messagesDiv = document.getElementById('messages');
    const chatTargetNameSpan = document.getElementById('chat-target-name'); // Was chat-with-username
    const chatTypeDisplaySpan = document.getElementById('chat-type-display');
    const userListUl = document.getElementById('user-list');
    const roomListUl = document.getElementById('room-list');
    const newRoomNameInput = document.getElementById('new-room-name'); // For create room form
    // Create room form is handled via standard POST, but we might refresh list via JS
    const inviteToRoomSection = document.getElementById('invite-to-room-section');
    const inviteUsernameInput = document.getElementById('invite-username-input');
    const inviteUserButton = document.getElementById('invite-user-button');


    // --- State Variables ---
    let currentChatType = 'dm'; // 'dm' or 'room'
    let currentChatTarget = null; // Username for DM, Room ID for room
    let mediaRecorder;
    let audioChunks = [];
    let timerInterval;
    let seconds = 0;
    window.socket = io(); // Make socket global for video_call.js too

    // --- Helper Functions ---
    function clearMessages() {
        messagesDiv.innerHTML = '';
    }

    function addMessageToUI(data) {
        const messageElement = document.createElement('div');
        if (data.message_type === 'audio') {
            messageElement.innerHTML = `
                <strong>${data.sender_username}:</strong>
                <audio controls src="${data.file_url}"></audio>
                <small>(${new Date(data.timestamp).toLocaleTimeString()})</small>`;
        } else { // Default to text
            messageElement.innerHTML = `
                <strong>${data.sender_username}:</strong> ${data.text}
                <small>(${new Date(data.timestamp).toLocaleTimeString()})</small>`;
        }
        messagesDiv.appendChild(messageElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    // --- Room Management ---
    async function fetchAndDisplayRooms() {
        try {
            const response = await fetch('/api/my_rooms');
            if (!response.ok) {
                console.error('Failed to fetch rooms:', response.statusText);
                return;
            }
            const rooms = await response.json();
            roomListUl.innerHTML = ''; // Clear existing list
            rooms.forEach(room => {
                const li = document.createElement('li');
                li.textContent = room.name;
                li.dataset.roomId = room.id;
                li.style.cursor = 'pointer';
                li.addEventListener('click', () => selectRoom(room));
                roomListUl.appendChild(li);
            });
        } catch (error) {
            console.error('Error fetching rooms:', error);
        }
    }
    
    function selectRoom(room) {
        if (currentChatType === 'room' && currentChatTarget === room.id) return; // Already in this room

        if (currentChatType === 'room' && currentChatTarget) {
            socket.emit('leave_room_event', { room_id: currentChatTarget });
        }

        currentChatType = 'room';
        currentChatTarget = room.id;
        chatTargetNameSpan.textContent = room.name;
        chatTypeDisplaySpan.textContent = 'Room';
        recipientUsernameInput.value = ''; // Clear DM recipient
        clearMessages();
        inviteToRoomSection.style.display = 'block';

        socket.emit('join_room_event', { room_id: room.id });
        
        // Fetch and display room messages
        fetch(`/api/room/${room.id}/messages`)
            .then(response => response.json())
            .then(messages => {
                messages.forEach(msg => addMessageToUI(msg));
            })
            .catch(error => console.error('Error fetching room messages:', error));
    }

    inviteUserButton.addEventListener('click', () => {
        const usernameToInvite = inviteUsernameInput.value.trim();
        if (!usernameToInvite) {
            alert('Please enter a username to invite.');
            return;
        }
        if (currentChatType !== 'room' || !currentChatTarget) {
            alert('Please select a room before inviting users.');
            return;
        }
        // Use a POST request for invite, as it modifies server-side state and has CSRF implications if not handled
        // For simplicity, constructing a form-like POST. Could also use fetch with POST.
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/invite_to_room/${currentChatTarget}/${usernameToInvite}`;
        
        // Add CSRF token if your app uses Flask-WTF CSRF protection globally
        // const csrfTokenInput = document.createElement('input');
        // csrfTokenInput.type = 'hidden';
        // csrfTokenInput.name = 'csrf_token'; 
        // csrfTokenInput.value = '{{ csrf_token() if csrf_token else "" }}'; // This template tag won't work in JS. Get from a meta tag or hidden input in HTML.
        // form.appendChild(csrfTokenInput);
        
        document.body.appendChild(form);
        form.submit();
        inviteUsernameInput.value = '';
    });


    // --- User (DM) Selection ---
    function selectUserForDM(user) {
        if (currentChatType === 'room' && currentChatTarget) {
            socket.emit('leave_room_event', { room_id: currentChatTarget });
            inviteToRoomSection.style.display = 'none';
        }
        currentChatType = 'dm';
        currentChatTarget = user.username;
        chatTargetNameSpan.textContent = user.username;
        chatTypeDisplaySpan.textContent = 'DM';
        recipientUsernameInput.value = user.username; // Set for sending logic
        clearMessages();
        // Fetch DM history (if implementing persistent DM history beyond session)
        // For now, DMs are live during session.
    }


    // --- Audio Recording Logic --- (Mostly unchanged, ensure it uses currentChatTarget and currentChatType)
    recordButton.addEventListener('click', async () => {
        if (!currentChatTarget) {
            alert('Please select a user or room to send a voice message to.');
            return;
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert('getUserMedia not supported on your browser!');
            return;
        }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                sendAudioBlob(audioBlob);
                audioChunks = [];
                stream.getTracks().forEach(track => track.stop());
            };
            mediaRecorder.start();
            recordButton.style.display = 'none';
            stopRecordButton.style.display = 'inline-block';
            timerSpan.style.display = 'inline';
            seconds = 0;
            timerSpan.textContent = '0s';
            timerInterval = setInterval(() => {
                seconds++;
                timerSpan.textContent = `${seconds}s`;
            }, 1000);
        } catch (err) {
            console.error('Error accessing microphone:', err);
            alert('Error accessing microphone. Please ensure permission is granted.');
        }
    });

    stopRecordButton.addEventListener('click', () => {
        if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
        recordButton.style.display = 'inline-block';
        stopRecordButton.style.display = 'none';
        timerSpan.style.display = 'none';
        clearInterval(timerInterval);
    });

    function sendAudioBlob(blob) {
        const payload = { audio_data: blob };
        if (currentChatType === 'room') {
            payload.room_id = currentChatTarget;
        } else if (currentChatType === 'dm') {
            payload.recipient_username = currentChatTarget;
        } else {
            alert('No active chat selected to send voice message.');
            return;
        }
        socket.emit('send_voice_message', payload);
    }

    // --- User List & DM Initialization ---
    function fetchUsers() {
        fetch('/users')
            .then(response => response.json())
            .then(users => {
                userListUl.innerHTML = '';
                users.forEach(user => {
                    const li = document.createElement('li');
                    li.textContent = user.username;
                    li.style.cursor = 'pointer';
                    li.addEventListener('click', () => selectUserForDM(user));
                    
                    const videoCallButton = document.createElement('button');
                    videoCallButton.textContent = 'Video Call';
                    videoCallButton.style.marginLeft = '10px';
                    videoCallButton.onclick = (event) => {
                        event.stopPropagation();
                        if (window.initiateVideoCall) window.initiateVideoCall(user.username);
                        else alert('Video call functionality not loaded.');
                    };
                    li.appendChild(videoCallButton);
                    userListUl.appendChild(li);
                });
            })
            .catch(error => console.error('Error fetching users:', error));
    }

    // --- Socket.IO Event Handlers ---
    socket.on('connect', () => {
        console.log('Connected to server');
        fetchUsers();
        fetchAndDisplayRooms(); // Fetch rooms on connect
    });

    socket.on('disconnect', () => console.log('Disconnected from server'));

    socket.on('status', (data) => {
        console.log('Status:', data.msg);
        // Could display status messages more prominently
    });

    socket.on('new_message', (data) => {
        console.log('Message received:', data);
        const currentUser = userListUl.dataset.currentUser;

        if (data.room_id) { // Room message
            if (currentChatType === 'room' && currentChatTarget === data.room_id) {
                addMessageToUI(data);
            } else {
                // Notify about message in another room
                console.log(`Message received for room ${data.room_id}, but not current view.`);
                // Highlight room in roomListUl or show unread count
            }
        } else if (data.recipient_username) { // DM
            if (currentChatType === 'dm' && 
                ((data.sender_username === currentUser && data.recipient_username === currentChatTarget) ||
                 (data.sender_username === currentChatTarget && data.recipient_username === currentUser))) {
                addMessageToUI(data);
            } else {
                 // Notify about DM from someone not in current view
                console.log(`DM received from/to ${data.sender_username}/${data.recipient_username}, but not current view.`);
            }
        }
    });

    socket.on('error', (data) => {
        console.error('Server error:', data.msg);
        alert('Error: ' + data.msg);
    });
    
    // Update room list when a new room is created (e.g. by this user from another tab, or if admin creates rooms)
    // This is a custom event you might need to emit from server after successful room creation via POST route
    socket.on('room_list_updated', () => {
        fetchAndDisplayRooms();
    });

    socket.on('user_joined_room_notification', (data) => {
        // Display this message if the user is currently in the affected room
        if (currentChatType === 'room' && currentChatTarget === data.room_id) {
            const messageElement = document.createElement('div');
            messageElement.style.fontStyle = 'italic';
            messageElement.style.color = 'grey';
            messageElement.textContent = `${data.username} has joined the room.`;
            messagesDiv.appendChild(messageElement);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        // Optionally, update a member list for the room if displayed
    });


    // --- Event Listeners (Text and Voice Message Sending) ---
    sendButton.addEventListener('click', () => {
        const text = messageInput.value.trim();
        if (!text) return;
        if (!currentChatTarget) {
            alert('Please select a user or room to chat with.');
            return;
        }

        const payload = { text: text, message_type: 'text' };
        if (currentChatType === 'room') {
            payload.room_id = currentChatTarget;
        } else { // dm
            payload.recipient_username = currentChatTarget;
        }
        socket.emit('send_message', payload);
        messageInput.value = '';
    });
    
    // For Create Room form submission, if we want to prevent default and handle via JS (optional)
    // document.getElementById('create-room-form').addEventListener('submit', function(event) {
    //     event.preventDefault();
    //     const roomName = newRoomNameInput.value.trim();
    //     if (roomName) {
    //         // Emit a socket event or use fetch to POST to /create_room
    //         // socket.emit('create_room_event', { room_name: roomName });
    //         // For now, it uses standard form POST, then page reload or manual refresh will update room list
    //         // Or, after successful POST, server could emit 'room_list_updated'
    //         this.submit(); // Proceed with normal form submission if not handling via JS fully
    //     }
    // });


    // --- Initial Setup ---
    fetchUsers();
    fetchAndDisplayRooms(); 
});

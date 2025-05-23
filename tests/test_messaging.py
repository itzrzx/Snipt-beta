import pytest
from app.models import Message, User
from app import db as _db # To avoid conflict with db fixture
import time

# --- Direct Messaging Tests ---

def test_send_receive_text_dm(app, db, auth_socketio_client, socketio_client_factory):
    """
    Test sending and receiving a direct text message between two users.
    """
    client_a, user_a = auth_socketio_client # User A is authenticated
    
    # Create and authenticate User B
    user_b_username = 'user_b_dm_text'
    user_b_email = 'user_b_dm_text@example.com'
    user_b_password = 'password123'
    user_b = User(username=user_b_username, email=user_b_email)
    user_b.set_password(user_b_password)
    db.session.add(user_b)
    db.session.commit()

    # Log in User B via HTTP to establish session for SocketIO
    http_client_b = app.test_client()
    http_client_b.post('/auth/login', data={'email': user_b_email, 'password': user_b_password}, follow_redirects=True)
    
    client_b = socketio_client_factory() # Create SocketIO client for User B
    assert client_b.is_connected()

    # User A sends a DM to User B
    dm_text = "Hello User B, this is a DM!"
    client_a.emit('send_message', {
        'recipient_username': user_b.username,
        'text': dm_text,
        'message_type': 'text' 
    })

    # Check if User A received their own message (echo)
    received_a = client_a.get_received()
    assert len(received_a) > 0
    dm_echo = None
    for msg_data in received_a:
        if msg_data['name'] == 'new_message' and msg_data['args'][0]['text'] == dm_text and msg_data['args'][0]['sender_username'] == user_a.username:
            dm_echo = msg_data['args'][0]
            break
    assert dm_echo is not None
    assert dm_echo['recipient_username'] == user_b.username

    # Check if User B received the message
    received_b = client_b.get_received()
    assert len(received_b) > 0
    dm_received = None
    for msg_data in received_b:
         if msg_data['name'] == 'new_message' and msg_data['args'][0]['text'] == dm_text and msg_data['args'][0]['sender_username'] == user_a.username:
            dm_received = msg_data['args'][0]
            break
    assert dm_received is not None
    assert dm_received['recipient_username'] == user_b.username
    
    # Check database
    db_message = Message.query.filter_by(body=dm_text, sender_id=user_a.id, recipient_id=user_b.id).first()
    assert db_message is not None
    assert db_message.room_id is None
    assert db_message.message_type == 'text'

    client_a.disconnect()
    client_b.disconnect()


def test_send_receive_voice_dm(app, db, auth_socketio_client, socketio_client_factory):
    """
    Test sending and receiving a direct voice message.
    File saving is mocked/bypassed; focus on event and DB record.
    """
    client_a, user_a = auth_socketio_client

    # Create and authenticate User B
    user_b_username = 'user_b_dm_voice'
    user_b_email = 'user_b_dm_voice@example.com'
    user_b_password = 'password123'
    user_b = User(username=user_b_username, email=user_b_email)
    user_b.set_password(user_b_password)
    db.session.add(user_b)
    db.session.commit()

    http_client_b = app.test_client()
    http_client_b.post('/auth/login', data={'email': user_b_email, 'password': user_b_password}, follow_redirects=True)
    client_b = socketio_client_factory()
    assert client_b.is_connected()

    mock_audio_data = b'fake_audio_data_blob'
    
    client_a.emit('send_voice_message', {
        'recipient_username': user_b.username,
        'audio_data': mock_audio_data 
        # 'message_type': 'audio' is implicit in the event name on server
    })

    # Check User A received echo
    received_a = client_a.get_received()
    voice_echo = None
    for msg_data in received_a:
        if msg_data['name'] == 'new_message' and msg_data['args'][0]['message_type'] == 'audio' and msg_data['args'][0]['sender_username'] == user_a.username:
            voice_echo = msg_data['args'][0]
            break
    assert voice_echo is not None
    assert voice_echo['recipient_username'] == user_b.username
    assert 'file_url' in voice_echo
    assert voice_echo['body'] == "[Voice Message]"

    # Check User B received message
    received_b = client_b.get_received()
    voice_received = None
    for msg_data in received_b:
        if msg_data['name'] == 'new_message' and msg_data['args'][0]['message_type'] == 'audio' and msg_data['args'][0]['sender_username'] == user_a.username:
            voice_received = msg_data['args'][0]
            break
    assert voice_received is not None
    assert voice_received['recipient_username'] == user_b.username
    assert 'file_url' in voice_received

    # Check database
    # We don't know the exact file_url due to uuid, so check other fields
    db_message = Message.query.filter_by(sender_id=user_a.id, recipient_id=user_b.id, message_type='audio').first()
    assert db_message is not None
    assert db_message.room_id is None
    assert db_message.body == "[Voice Message]"
    assert db_message.file_url is not None 
    assert '.webm' in db_message.file_url # Default extension used in backend

    client_a.disconnect()
    client_b.disconnect()

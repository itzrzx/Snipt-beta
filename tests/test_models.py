import pytest
from app.models import User, Message, Room, RoomMember
from app import db as _db # To avoid conflict with the db fixture
from sqlalchemy.exc import IntegrityError

# --- User Model Tests ---
def test_user_creation(db):
    user = User(username='newuser', email='new@example.com')
    user.set_password('newpassword')
    db.session.add(user)
    db.session.commit()

    retrieved_user = User.query.filter_by(username='newuser').first()
    assert retrieved_user is not None
    assert retrieved_user.email == 'new@example.com'
    assert retrieved_user.check_password('newpassword')
    assert not retrieved_user.check_password('wrongpassword')

def test_user_uniqueness(db, test_user): # test_user fixture from conftest.py
    # test_user is already 'testuser', 'test@example.com'
    
    # Test duplicate username
    with pytest.raises(IntegrityError):
        user_dup_username = User(username='testuser', email='another@example.com')
        user_dup_username.set_password('password')
        db.session.add(user_dup_username)
        db.session.commit()
    db.session.rollback() # Rollback session after expected error

    # Test duplicate email
    with pytest.raises(IntegrityError):
        user_dup_email = User(username='anotheruser', email='test@example.com')
        user_dup_email.set_password('password')
        db.session.add(user_dup_email)
        db.session.commit()
    db.session.rollback()

# --- Message Model Tests ---
def test_dm_message_creation(db, test_user):
    user2 = User(username='user2', email='user2@example.com')
    user2.set_password('password')
    db.session.add(user2)
    db.session.commit()

    msg = Message(sender_id=test_user.id, recipient_id=user2.id, body="Hello DM!")
    db.session.add(msg)
    db.session.commit()

    retrieved_msg = Message.query.first()
    assert retrieved_msg is not None
    assert retrieved_msg.sender_id == test_user.id
    assert retrieved_msg.recipient_id == user2.id
    assert retrieved_msg.room_id is None
    assert retrieved_msg.body == "Hello DM!"
    assert retrieved_msg.timestamp is not None
    assert retrieved_msg.message_type == 'text'

def test_room_message_creation(db, test_user):
    # Create a room first
    room = Room(name='Test Room For Message', creator_id=test_user.id)
    db.session.add(room)
    db.session.commit() # Commit to get room.id

    # Add test_user as a member (though not strictly required for sending if no check, good practice)
    member = RoomMember(user_id=test_user.id, room_id=room.id)
    db.session.add(member)
    db.session.commit()
    
    msg = Message(sender_id=test_user.id, room_id=room.id, body="Hello Room!")
    db.session.add(msg)
    db.session.commit()

    retrieved_msg = Message.query.filter_by(room_id=room.id).first()
    assert retrieved_msg is not None
    assert retrieved_msg.sender_id == test_user.id
    assert retrieved_msg.room_id == room.id
    assert retrieved_msg.recipient_id is None
    assert retrieved_msg.body == "Hello Room!"

def test_voice_message_creation(db, test_user):
    user2 = User(username='user2_voice', email='user2_voice@example.com') # Ensure unique
    user2.set_password('password')
    db.session.add(user2)
    db.session.commit()

    voice_msg = Message(sender_id=test_user.id, recipient_id=user2.id, 
                        message_type='audio', file_url='/uploads/someaudio.webm', body="[Voice Message]")
    db.session.add(voice_msg)
    db.session.commit()
    
    retrieved_msg = Message.query.filter_by(message_type='audio').first()
    assert retrieved_msg is not None
    assert retrieved_msg.file_url == '/uploads/someaudio.webm'
    assert retrieved_msg.message_type == 'audio'

# --- Room Model Tests ---
def test_room_creation(db, test_user):
    room = Room(name='Awesome Room', creator_id=test_user.id)
    db.session.add(room)
    db.session.commit()

    retrieved_room = Room.query.filter_by(name='Awesome Room').first()
    assert retrieved_room is not None
    assert retrieved_room.creator_id == test_user.id
    assert retrieved_room.creator.username == test_user.username
    assert retrieved_room.created_at is not None

# --- RoomMember Model Tests ---
def test_room_member_creation(db, test_user):
    room = Room(name='Membership Test Room', creator_id=test_user.id)
    db.session.add(room)
    db.session.commit() # Commit to get room.id

    member = RoomMember(user_id=test_user.id, room_id=room.id)
    db.session.add(member)
    db.session.commit()

    retrieved_member = RoomMember.query.filter_by(user_id=test_user.id, room_id=room.id).first()
    assert retrieved_member is not None
    assert retrieved_member.user_id == test_user.id
    assert retrieved_member.room_id == room.id
    assert retrieved_member.joined_at is not None
    assert retrieved_member.user == test_user
    assert retrieved_member.room == room
    
    # Test uniqueness constraint for RoomMember
    with pytest.raises(IntegrityError):
        duplicate_member = RoomMember(user_id=test_user.id, room_id=room.id)
        db.session.add(duplicate_member)
        db.session.commit()
    db.session.rollback()

    # Test if user is part of room's members collection
    # Re-fetch user from session to ensure relationship is active in the current session context
    db_test_user = _db.session.get(User, test_user.id) # Use _db from import
    assert db_test_user.rooms.filter_by(room_id=room.id).first() is not None
    
    # Test if room has this member in its members collection
    db_room = _db.session.get(Room, room.id) # Use _db from import
    assert db_room.members.filter_by(user_id=test_user.id).first() is not None

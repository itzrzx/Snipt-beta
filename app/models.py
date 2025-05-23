from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime # Import datetime
from flask_login import UserMixin # Import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model): # Inherit from UserMixin
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='author', lazy='dynamic')
    messages_received = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient_user', lazy='dynamic') # Renamed backref to avoid conflict
    rooms = db.relationship('RoomMember', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140), nullable=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Nullable for room messages
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=True) # For room messages
    message_type = db.Column(db.String(10), default='text') 
    file_url = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return '<Message {}:{}>'.format(self.message_type, self.body if self.message_type == 'text' else self.file_url)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # Changed from VARCHAR(255) to String(100) to match typical Flask-SQLAlchemy
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Added nullable=False
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('User', backref='created_rooms')
    messages = db.relationship('Message', backref='room', lazy='dynamic')
    members = db.relationship('RoomMember', back_populates='room', cascade="all, delete-orphan", lazy='dynamic') # Add lazy='dynamic'

    def __repr__(self):
        return f'<Room {self.name}>'

class RoomMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='rooms')
    room = db.relationship('Room', back_populates='members')

    __table_args__ = (db.UniqueConstraint('user_id', 'room_id', name='_user_room_uc'),)

    def __repr__(self):
        return f'<RoomMember user_id={self.user_id} room_id={self.room_id}>'

from flask import render_template, jsonify
from flask_login import login_required, current_user
from app.main import bp
from app.models import User # Import User model

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    return render_template('index.html', title='Home', current_user_username=current_user.username)

@bp.route('/users')
@login_required
def users():
    users = User.query.filter(User.id != current_user.id).all()
    return jsonify([{'username': user.username, 'id': user.id} for user in users])

# Route to serve uploaded voice messages
from flask import current_app, send_from_directory
import os

@bp.route('/uploads/voice_messages/<path:filename>')
@login_required # Optional: Protect access to voice messages
def uploaded_voice_message(filename):
    # UPLOAD_FOLDER is already an absolute path to app/uploads/voice_messages
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

from flask import request, flash, redirect, url_for # Add redirect, url_for
from app.models import Room, RoomMember # Import Room and RoomMember
from app import db # Import db

@bp.route('/create_room', methods=['POST'])
@login_required
def create_room():
    room_name = request.form.get('room_name')
    if not room_name:
        flash('Room name is required.', 'error')
        return redirect(url_for('main.index')) # Or wherever your main chat page is

    existing_room_by_user = Room.query.filter_by(name=room_name, creator_id=current_user.id).first()
    if existing_room_by_user:
        flash(f'You already have a room named "{room_name}". Choose a different name.', 'warning')
        return redirect(url_for('main.index'))

    new_room = Room(name=room_name, creator_id=current_user.id)
    db.session.add(new_room)
    db.session.flush() # To get new_room.id for RoomMember

    # Add current user as the first member
    first_member = RoomMember(user_id=current_user.id, room_id=new_room.id)
    db.session.add(first_member)
    db.session.commit()

    flash(f'Room "{room_name}" created successfully!', 'success')
    
    from app import socketio # Import socketio instance
    # Emit to the creator of the room so their list updates.
    # If this needs to be broader, adjust accordingly.
    socketio.emit('room_list_updated', room=current_user.username) 
    # A more robust approach might be to emit to all users or specific groups if rooms are public or auto-joined.
    # For now, this updates the creator's list. Other users' lists would update on next connect/refresh 
    # unless invited, in which case an event specific to the invitee should also be considered.

    return redirect(url_for('main.index'))

@bp.route('/invite_to_room/<int:room_id>/<string:username>', methods=['POST'])
@login_required
def invite_to_room(room_id, username):
    room = Room.query.get_or_404(room_id)
    
    # Check if current user is a member of the room (or creator for more strictness)
    is_member = RoomMember.query.filter_by(user_id=current_user.id, room_id=room.id).first()
    if not is_member and room.creator_id != current_user.id: # Allow creator to invite even if not explicitly a member yet (though create_room adds them)
        flash('You are not authorized to invite users to this room.', 'error')
        return redirect(url_for('main.index'))

    user_to_invite = User.query.filter_by(username=username).first()
    if not user_to_invite:
        flash(f'User "{username}" not found.', 'error')
        return redirect(url_for('main.index')) # Or back to a room management page

    if user_to_invite.id == current_user.id:
        flash('You cannot invite yourself to a room.', 'warning')
        return redirect(url_for('main.index'))

    existing_membership = RoomMember.query.filter_by(user_id=user_to_invite.id, room_id=room.id).first()
    if existing_membership:
        flash(f'User "{username}" is already a member of room "{room.name}".', 'info')
        return redirect(url_for('main.index'))

    new_member = RoomMember(user_id=user_to_invite.id, room_id=room.id)
    db.session.add(new_member)
    db.session.commit()

    flash(f'User "{username}" has been added to room "{room.name}".', 'success')
    
    from app import socketio # Import socketio instance
    # Notify the invited user that their room list should be updated
    socketio.emit('room_list_updated', room=username) # Assuming username is the SocketIO room for this user
    # Notify existing members of the room that a new user has joined (optional)
    socketio_room_name = f'room_{room.id}'
    socketio.emit('user_joined_room_notification', {'username': username, 'room_name': room.name, 'room_id': room.id}, room=socketio_room_name)
    
    return redirect(url_for('main.index'))

@bp.route('/api/my_rooms', methods=['GET'])
@login_required
def my_rooms():
    # Query RoomMember for rooms associated with current_user.id
    # Then join with Room to get room names and other details
    user_room_memberships = RoomMember.query.filter_by(user_id=current_user.id).all()
    rooms_data = []
    for membership in user_room_memberships:
        room = Room.query.get(membership.room_id)
        if room:
            rooms_data.append({
                'id': room.id,
                'name': room.name,
                'creator_id': room.creator_id
                # Add other room details if needed
            })
    return jsonify(rooms_data)

@bp.route('/api/room/<int:room_id>/messages', methods=['GET'])
@login_required
def get_room_messages(room_id):
    # Verify current user is a member of the room
    is_member = RoomMember.query.filter_by(user_id=current_user.id, room_id=room_id).first()
    if not is_member:
        return jsonify({'error': 'Not authorized to view messages for this room.'}), 403

    room_messages = Message.query.filter_by(room_id=room_id).order_by(Message.timestamp.asc()).all()
    messages_data = []
    for msg in room_messages:
        sender = User.query.get(msg.sender_id) # Get sender's username
        messages_data.append({
            'id': msg.id,
            'sender_username': sender.username if sender else 'Unknown',
            'body': msg.body,
            'timestamp': msg.timestamp.isoformat(),
            'message_type': msg.message_type,
            'file_url': msg.file_url
            # Add other message details if needed
        })
    return jsonify(messages_data)

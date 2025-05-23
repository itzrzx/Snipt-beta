from flask import request, current_app # Added current_app
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from app import db, socketio # Import socketio from app
from app.models import User, Message
import os # For file operations
import uuid # For unique filenames

# Dictionary to store username to SID mappings
user_sids = {}

@socketio.on('connect')
def connect():
    if current_user.is_authenticated:
        # Personal room for DMs and system messages (WebRTC signaling also uses this)
        join_room(current_user.username) 
        user_sids[current_user.username] = request.sid # For WebRTC SID mapping
        print(f"User {current_user.username} connected (SID: {request.sid}), joined personal room '{current_user.username}'.")
        emit('status', {'msg': current_user.username + ' has connected.'}, room=current_user.username) # Emit to user's personal room
    else:
        print(f"Unauthenticated user connected with SID {request.sid}")


@socketio.on('disconnect')
def disconnect():
    if current_user.is_authenticated and current_user.username in user_sids:
        if user_sids.get(current_user.username) == request.sid: # Check if it's the same session
            del user_sids[current_user.username] # For WebRTC
        # Flask-SocketIO automatically handles removing client from rooms it joined, including current_user.username room
        print(f"User {current_user.username} disconnected (SID: {request.sid}).")
    else:
        print(f"User (unknown or not in sids) disconnected (SID: {request.sid}).")


@socketio.on('send_message') # Renamed from send_message to handle_send_message for clarity if needed, but keeping 'send_message' for API consistency
def handle_send_message(data): # Changed function name for internal clarity if desired, but event name is key
    if not current_user.is_authenticated:
        emit('error', {'msg': 'Authentication required.'})
        return

    text = data.get('text')
    room_id = data.get('room_id')
    recipient_username = data.get('recipient_username') # For DMs

    if not text:
        emit('error', {'msg': 'Message text cannot be empty.'})
        return

    message_payload_base = {
        'sender_username': current_user.username,
        'text': text,
        'message_type': 'text',
        # timestamp will be added after DB commit
    }

    if room_id: # Room message
        from app.models import RoomMember # Local import to avoid potential circularity if models ever import socketio
        is_member = RoomMember.query.filter_by(user_id=current_user.id, room_id=room_id).first()
        if not is_member:
            emit('error', {'msg': 'You are not a member of this room.'})
            return
        
        message = Message(sender_id=current_user.id, room_id=int(room_id), body=text, message_type='text')
        db.session.add(message)
        db.session.commit()
        
        message_payload = message_payload_base.copy()
        message_payload['room_id'] = int(room_id)
        message_payload['timestamp'] = message.timestamp.isoformat()
        
        socketio_room_name = f'room_{room_id}'
        emit('new_message', message_payload, room=socketio_room_name)
        print(f"Message from {current_user.username} to room {room_id} ('{socketio_room_name}'): {text}")

    elif recipient_username: # Direct message
        recipient = User.query.filter_by(username=recipient_username).first()
        if not recipient:
            emit('error', {'msg': f'Recipient {recipient_username} not found.'})
            return
        
        message = Message(sender_id=current_user.id, recipient_id=recipient.id, body=text, message_type='text')
        db.session.add(message)
        db.session.commit()

        message_payload = message_payload_base.copy()
        message_payload['recipient_username'] = recipient_username
        message_payload['timestamp'] = message.timestamp.isoformat()

        emit('new_message', message_payload, room=recipient.username) # To recipient
        emit('new_message', message_payload, room=current_user.username) # Echo to sender
        print(f"DM from {current_user.username} to {recipient_username}: {text}")
    else:
        emit('error', {'msg': 'Message must have a recipient or a room.'})


@socketio.on('send_voice_message') # Renamed from send_voice_message for internal clarity if desired
def handle_send_voice_message(data): # Changed function name
    if not current_user.is_authenticated:
        emit('error', {'msg': 'Authentication required.'})
        return

    audio_data = data.get('audio_data')
    room_id = data.get('room_id')
    recipient_username = data.get('recipient_username')

    if not audio_data:
        emit('error', {'msg': 'Audio data is required.'})
        return
    if not room_id and not recipient_username:
        emit('error', {'msg': 'Voice message must have a recipient or a room.'})
        return
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    filename = str(uuid.uuid4()) + '.webm'
    filepath = os.path.join(upload_folder, filename)
    file_url = '/uploads/voice_messages/' + filename
    try:
        with open(filepath, 'wb') as f:
            f.write(audio_data)
    except Exception as e:
        emit('error', {'msg': f'Failed to save voice message: {str(e)}'})
        return

    message_payload_base = {
        'sender_username': current_user.username,
        'message_type': 'audio',
        'file_url': file_url,
        'body': '[Voice Message]' 
    }

    if room_id:
        from app.models import RoomMember 
        is_member = RoomMember.query.filter_by(user_id=current_user.id, room_id=room_id).first()
        if not is_member:
            emit('error', {'msg': 'You are not a member of this room.'})
            return
        
        message = Message(sender_id=current_user.id, room_id=int(room_id), 
                          message_type='audio', file_url=file_url, body='[Voice Message]')
        db.session.add(message)
        db.session.commit()

        message_payload = message_payload_base.copy()
        message_payload['room_id'] = int(room_id)
        message_payload['timestamp'] = message.timestamp.isoformat()
        
        socketio_room_name = f'room_{room_id}'
        emit('new_message', message_payload, room=socketio_room_name)
        print(f"Voice message from {current_user.username} to room {room_id} ('{socketio_room_name}')")

    elif recipient_username:
        recipient = User.query.filter_by(username=recipient_username).first()
        if not recipient:
            emit('error', {'msg': f'Recipient {recipient_username} not found.'})
            return
            
        message = Message(sender_id=current_user.id, recipient_id=recipient.id, 
                          message_type='audio', file_url=file_url, body='[Voice Message]')
        db.session.add(message)
        db.session.commit()

        message_payload = message_payload_base.copy()
        message_payload['recipient_username'] = recipient_username
        message_payload['timestamp'] = message.timestamp.isoformat()

        emit('new_message', message_payload, room=recipient.username)
        emit('new_message', message_payload, room=current_user.username)
        print(f"Voice DM from {current_user.username} to {recipient_username}")

@socketio.on('join_room_event')
def handle_join_room_event(data):
    if not current_user.is_authenticated:
        emit('error', {'msg': 'Authentication required.'})
        return
    
    room_id = data.get('room_id')
    if not room_id:
        emit('error', {'msg': 'Room ID is required.'})
        return

    from app.models import RoomMember 
    is_member = RoomMember.query.filter_by(user_id=current_user.id, room_id=room_id).first()
    if not is_member:
        emit('error', {'msg': 'You are not a member of this room.'})
        return
    
    socketio_room_name = f'room_{room_id}'
    join_room(socketio_room_name) # SID joins this SocketIO room
    print(f"User {current_user.username} (SID: {request.sid}) joined SocketIO room '{socketio_room_name}' for chat room ID {room_id}")
    
    emit('status', {'msg': f'You joined room {room_id}. Messages will now be live.'}, room=request.sid) 


@socketio.on('leave_room_event')
def handle_leave_room_event(data):
    if not current_user.is_authenticated:
        return
        
    room_id = data.get('room_id')
    if not room_id:
        return

    socketio_room_name = f'room_{room_id}'
    leave_room(socketio_room_name) # SID leaves this SocketIO room
    print(f"User {current_user.username} (SID: {request.sid}) left SocketIO room '{socketio_room_name}' for chat room ID {room_id}")
    emit('status', {'msg': f'You left room {room_id}.'}, room=request.sid)


# --- WebRTC Signaling Handlers ---

@socketio.on('initiate_call')
def handle_initiate_call(data):
    callee_username = data.get('callee_username')
    caller_username = data.get('caller_username') # Should be current_user.username

    if not current_user.is_authenticated or current_user.username != caller_username:
        emit('error', {'msg': 'Authentication error or username mismatch.'})
        return

    callee_sid = user_sids.get(callee_username)
    if callee_sid:
        print(f"Relaying 'call_offer_request' from {caller_username} to {callee_username} (SID: {callee_sid})")
        emit('call_offer_request', {'caller_username': caller_username}, room=callee_sid)
    else:
        print(f"Callee {callee_username} not found or not connected.")
        # Optionally, inform the caller that the callee is not available
        emit('error', {'msg': f'User {callee_username} is not online.'}, room=request.sid)

@socketio.on('offer_sdp')
def handle_offer_sdp(data):
    target_username = data.get('target_username') # This is the callee
    caller_username = data.get('caller_username') # This is the sender of the offer
    sdp = data.get('sdp')

    if not current_user.is_authenticated or current_user.username != caller_username:
        emit('error', {'msg': 'Authentication error or username mismatch for offer.'})
        return

    target_sid = user_sids.get(target_username)
    if target_sid:
        print(f"Relaying 'offer_sdp' from {caller_username} to {target_username} (SID: {target_sid})")
        emit('offer_sdp_received', {'sdp': sdp, 'caller_username': caller_username}, room=target_sid)
    else:
        print(f"Target {target_username} for SDP offer not found.")
        emit('error', {'msg': f'User {target_username} is not online for offer.'}, room=request.sid)


@socketio.on('answer_sdp')
def handle_answer_sdp(data):
    target_username = data.get('target_username') # This is the original caller
    callee_username = data.get('callee_username') # This is the sender of the answer
    sdp = data.get('sdp')

    if not current_user.is_authenticated or current_user.username != callee_username:
        emit('error', {'msg': 'Authentication error or username mismatch for answer.'})
        return

    target_sid = user_sids.get(target_username)
    if target_sid:
        print(f"Relaying 'answer_sdp' from {callee_username} to {target_username} (SID: {target_sid})")
        emit('answer_sdp_received', {'sdp': sdp, 'callee_username': callee_username}, room=target_sid)
    else:
        print(f"Target {target_username} for SDP answer not found.")
        emit('error', {'msg': f'User {target_username} is not online for answer.'}, room=request.sid)

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    target_username = data.get('target_username')
    sender_username = data.get('sender_username') # Should be current_user.username
    candidate = data.get('candidate')

    if not current_user.is_authenticated or current_user.username != sender_username:
        emit('error', {'msg': 'Authentication error or username mismatch for ICE candidate.'})
        return

    target_sid = user_sids.get(target_username)
    if target_sid:
        # print(f"Relaying 'ice_candidate' from {sender_username} to {target_username} (SID: {target_sid})")
        emit('ice_candidate_received', {'candidate': candidate, 'sender_username': sender_username}, room=target_sid)
    else:
        # This can happen if the other user disconnects during ICE exchange
        print(f"Target {target_username} for ICE candidate not found.")
        # No need to emit error back for ICE usually, as connection might just fail.

@socketio.on('hang_up')
def handle_hang_up(data):
    target_username = data.get('target_username')
    sender_username = data.get('sender_username') # Should be current_user.username

    if not current_user.is_authenticated or current_user.username != sender_username:
        emit('error', {'msg': 'Authentication error or username mismatch for hang_up.'})
        return

    target_sid = user_sids.get(target_username)
    if target_sid:
        print(f"Relaying 'hang_up' from {sender_username} to {target_username} (SID: {target_sid})")
        emit('call_hanged_up', {'sender_username': sender_username}, room=target_sid)
    else:
        print(f"Target {target_username} for hang_up not found.")

@socketio.on('call_rejected')
def handle_call_rejected(data):
    caller_username = data.get('caller_username') # Original caller to notify
    callee_username = data.get('callee_username') # The one who rejected, current_user.username

    if not current_user.is_authenticated or current_user.username != callee_username:
        emit('error', {'msg': 'Authentication error or username mismatch for call_rejected.'})
        return
        
    caller_sid = user_sids.get(caller_username)
    if caller_sid:
        print(f"Relaying 'call_rejected_by_peer' from {callee_username} to {caller_username} (SID: {caller_sid})")
        emit('call_rejected_by_peer', {'callee_username': callee_username}, room=caller_sid)
    else:
        print(f"Caller {caller_username} for call_rejected notification not found.")

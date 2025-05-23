document.addEventListener('DOMContentLoaded', () => {
    // Socket.IO instance will be taken from chat.js or initialized if separate
    // For now, assume `socket` is globally available from chat.js or initialize a new one.
    // const socket = io(); // Or get it from chat.js

    // UI Elements
    const localVideo = document.getElementById('localVideo');
    const remoteVideo = document.getElementById('remoteVideo');
    const endCallButton = document.getElementById('end-call-button');
    const videoCallUI = document.getElementById('video-call-ui');
    const callStatus = document.getElementById('call-status');
    const incomingCallAlert = document.getElementById('incoming-call-alert');
    const callerUsernameSpan = document.getElementById('caller-username-span');
    const acceptCallButton = document.getElementById('accept-call-button');
    const rejectCallButton = document.getElementById('reject-call-button');

    // WebRTC Globals
    let localStream;
    let peerConnection;
    let targetUsernameGlobal; // The user we are calling or is calling us
    let myUsernameGlobal; // Set this from a data attribute or similar

    const peerConnectionConfig = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            // Add TURN servers here if available and needed
        ]
    };

    // Function to initialize and start local media
    async function startLocalMedia() {
        try {
            localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            localVideo.srcObject = localStream;
            callStatus.textContent = 'Local media started.';
            return true;
        } catch (error) {
            console.error('Error accessing local media:', error);
            callStatus.textContent = 'Error accessing camera/microphone. Please check permissions.';
            alert('Error accessing camera/microphone: ' + error.message);
            return false;
        }
    }

    // Function to create and configure RTCPeerConnection
    function createPeerConnection() {
        peerConnection = new RTCPeerConnection(peerConnectionConfig);

        // Add local stream tracks
        if (localStream) {
            localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
        }

        // Handle incoming remote tracks
        peerConnection.ontrack = event => {
            if (event.streams && event.streams[0]) {
                remoteVideo.srcObject = event.streams[0];
                callStatus.textContent = 'Remote stream received.';
            } else {
                // Fallback for older browsers
                let inboundStream = new MediaStream(event.track);
                remoteVideo.srcObject = inboundStream;
            }
        };

        // Handle ICE candidates
        peerConnection.onicecandidate = event => {
            if (event.candidate && targetUsernameGlobal) {
                console.log('Sending ICE candidate to', targetUsernameGlobal);
                // Placeholder: Signaling for ICE candidates will be added later
                // socket.emit('ice_candidate', { 'target_username': targetUsernameGlobal, 'candidate': event.candidate });
            }
        };
        
        peerConnection.oniceconnectionstatechange = () => {
            console.log('ICE connection state change:', peerConnection.iceConnectionState);
            callStatus.textContent = `ICE Connection: ${peerConnection.iceConnectionState}`;
            if (peerConnection.iceConnectionState === 'connected' || peerConnection.iceConnectionState === 'completed') {
                 videoCallUI.style.display = 'block'; // Ensure UI is visible
            }
        };

        console.log('RTCPeerConnection created.');
    }
    
    // --- Call Control Functions ---
    window.initiateVideoCall = async (targetUsername) => {
        if (!targetUsername) {
            alert('Target user not specified.');
            return;
        }
        targetUsernameGlobal = targetUsername;
        myUsernameGlobal = document.getElementById('user-list').dataset.currentUser; // Assuming this is set in chat.js

        callStatus.textContent = `Initiating call with ${targetUsername}...`;
        videoCallUI.style.display = 'block';

        if (!await startLocalMedia()) return;
        
        // Placeholder: Signaling for initiating call
        // socket.emit('initiate_call', { 'callee_username': targetUsername });
        console.log(`Initiating call to ${targetUsername}. My username: ${myUsernameGlobal}`);
        // createPeerConnection(); // Create PC after local media, before offer
        // Further logic for offer creation will be here
    };

    endCallButton.addEventListener('click', () => {
        callStatus.textContent = 'Ending call...';
        // Placeholder: Signaling for hang_up
        // if (targetUsernameGlobal) {
        //     socket.emit('hang_up', { 'target_username': targetUsernameGlobal });
        // }
        closeVideoCall();
    });

    function closeVideoCall() {
        if (peerConnection) {
            peerConnection.close();
            peerConnection = null;
        }
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
            localStream = null;
        }
        localVideo.srcObject = null;
        remoteVideo.srcObject = null;
        videoCallUI.style.display = 'none';
        incomingCallAlert.style.display = 'none';
        targetUsernameGlobal = null;
        callStatus.textContent = 'Call ended.';
        console.log('Video call closed.');
    }

    // --- Incoming Call Handling ---
    acceptCallButton.addEventListener('click', async () => {
        incomingCallAlert.style.display = 'none';
        videoCallUI.style.display = 'block';
        callStatus.textContent = `Accepting call from ${targetUsernameGlobal}...`;
        
        if (!await startLocalMedia()) {
            // Send reject if media fails?
            // socket.emit('call_rejected', { 'caller_username': targetUsernameGlobal });
            closeVideoCall();
            return;
        }
        // createPeerConnection(); // Create PC after local media, before answer
        // Placeholder: Further logic for answer creation will be here
        console.log(`Accepted call from ${targetUsernameGlobal}. My username: ${myUsernameGlobal}`);
    });

    rejectCallButton.addEventListener('click', () => {
        incomingCallAlert.style.display = 'none';
        // Placeholder: Signaling for rejecting call
        // if (targetUsernameGlobal) {
        //     socket.emit('call_rejected', { 'caller_username': targetUsernameGlobal });
        // }
        callStatus.textContent = `Call from ${targetUsernameGlobal} rejected.`;
        targetUsernameGlobal = null; // Clear target as call is rejected
        console.log('Call rejected.');
    });

    // Placeholder for receiving call offer request from server
    // This will be triggered by a SocketIO event from the server
    window.handleIncomingCall = (data) => {
        // data should be like {'caller_username': 'UserA', 'caller_sid': 'some_sid'}
        targetUsernameGlobal = data.caller_username; // This is the caller
        myUsernameGlobal = document.getElementById('user-list').dataset.currentUser;

        callerUsernameSpan.textContent = targetUsernameGlobal;
        incomingCallAlert.style.display = 'block';
        callStatus.textContent = `Incoming call from ${targetUsernameGlobal}...`;
        console.log(`Incoming call from ${targetUsernameGlobal}. My username: ${myUsernameGlobal}`);
    };
    
    const socket = window.socket; // Assume socket is globally available from chat.js

    // --- Call Control Functions (Modified for Signaling) ---
    window.initiateVideoCall = async (targetUsername) => {
        if (!targetUsername) {
            alert('Target user not specified.');
            return;
        }
        targetUsernameGlobal = targetUsername;
        myUsernameGlobal = document.getElementById('user-list').dataset.currentUser;

        callStatus.textContent = `Initiating call with ${targetUsername}...`;
        videoCallUI.style.display = 'block';

        if (!await startLocalMedia()) {
            closeVideoCall(); // Clean up if media fails
            return;
        }
        
        createPeerConnection(); // Create PC after local media, before offer

        // Send initiate_call to server
        console.log(`Emitting initiate_call to ${targetUsername}. My username: ${myUsernameGlobal}`);
        socket.emit('initiate_call', { 'callee_username': targetUsernameGlobal, 'caller_username': myUsernameGlobal });
        // Offer creation will be triggered by a server response or another UI action if needed
        // For now, let's assume we create offer right after initiate_call for simplicity in this step
        try {
            const offer = await peerConnection.createOffer();
            await peerConnection.setLocalDescription(offer);
            console.log('Offer created and local description set. Emitting offer_sdp.');
            socket.emit('offer_sdp', { 
                'target_username': targetUsernameGlobal, 
                'caller_username': myUsernameGlobal,
                'sdp': offer 
            });
            callStatus.textContent = 'Offer sent. Waiting for answer...';
        } catch (error) {
            console.error('Error creating offer:', error);
            callStatus.textContent = 'Error creating call offer.';
            closeVideoCall();
        }
    };

    endCallButton.addEventListener('click', () => {
        callStatus.textContent = 'Ending call...';
        if (targetUsernameGlobal) {
            socket.emit('hang_up', { 'target_username': targetUsernameGlobal, 'sender_username': myUsernameGlobal });
        }
        closeVideoCall();
    });
    
    acceptCallButton.addEventListener('click', async () => {
        incomingCallAlert.style.display = 'none';
        videoCallUI.style.display = 'block';
        callStatus.textContent = `Accepting call from ${targetUsernameGlobal}...`;
        
        if (!await startLocalMedia()) {
            socket.emit('call_rejected', { 'caller_username': targetUsernameGlobal, 'callee_username': myUsernameGlobal });
            closeVideoCall();
            return;
        }
        createPeerConnection(); // Create PC after local media, before answer
        
        // The offer SDP is expected to be passed via handleOfferSDP before this.
        // Here we just notify acceptance. The actual answer generation happens after offer is set.
        console.log(`Call accepted from ${targetUsernameGlobal}. My username: ${myUsernameGlobal}. Waiting for offer to create answer.`);
        // Answer will be created in handleOfferSDP after setting remote description
    });

    rejectCallButton.addEventListener('click', () => {
        incomingCallAlert.style.display = 'none';
        if (targetUsernameGlobal) {
            socket.emit('call_rejected', { 'caller_username': targetUsernameGlobal, 'callee_username': myUsernameGlobal });
        }
        callStatus.textContent = `Call from ${targetUsernameGlobal} rejected.`;
        targetUsernameGlobal = null; 
        closeVideoCall(); // Ensure cleanup
        console.log('Call rejected.');
    });

    // Modified onicecandidate to use targetUsernameGlobal
    function createPeerConnection() { // Ensure this is called correctly
        peerConnection = new RTCPeerConnection(peerConnectionConfig);
        if (localStream) {
            localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
        }
        peerConnection.ontrack = event => {
            remoteVideo.srcObject = event.streams && event.streams[0] ? event.streams[0] : new MediaStream([event.track]);
            callStatus.textContent = 'Remote stream received.';
        };
        peerConnection.onicecandidate = event => {
            if (event.candidate && targetUsernameGlobal) {
                console.log('Sending ICE candidate to', targetUsernameGlobal);
                socket.emit('ice_candidate', { 
                    'target_username': targetUsernameGlobal, 
                    'sender_username': myUsernameGlobal,
                    'candidate': event.candidate 
                });
            }
        };
        peerConnection.oniceconnectionstatechange = () => {
            console.log('ICE connection state change:', peerConnection.iceConnectionState);
            callStatus.textContent = `ICE Connection: ${peerConnection.iceConnectionState}`;
            if (peerConnection.iceConnectionState === 'connected' || peerConnection.iceConnectionState === 'completed') {
                 videoCallUI.style.display = 'block';
            } else if (peerConnection.iceConnectionState === 'failed' || peerConnection.iceConnectionState === 'disconnected' || peerConnection.iceConnectionState === 'closed') {
                // Optionally auto-close call on failed/disconnected, or provide reconnect UI
                // closeVideoCall(); 
            }
        };
        console.log('RTCPeerConnection created and configured.');
    }
    
    // --- SocketIO Signaling Event Handlers ---
    socket.on('call_offer_request', (data) => {
        // data: {'caller_username': 'UserA'}
        // Note: Server now sends caller_username directly, SID mapping is server-side.
        targetUsernameGlobal = data.caller_username; // This is the caller
        myUsernameGlobal = document.getElementById('user-list').dataset.currentUser;

        callerUsernameSpan.textContent = targetUsernameGlobal;
        incomingCallAlert.style.display = 'block';
        callStatus.textContent = `Incoming call from ${targetUsernameGlobal}...`;
        console.log(`Incoming call_offer_request from ${targetUsernameGlobal}. My username: ${myUsernameGlobal}`);
        // User will click Accept or Reject. If Accept, then we wait for 'offer_sdp_received'.
    });

    socket.on('offer_sdp_received', async (data) => {
        // data: {'sdp': offer, 'caller_username': 'UserA'}
        console.log('Offer SDP received from', data.caller_username);
        targetUsernameGlobal = data.caller_username; // Caller becomes the target for answer/ICE
        myUsernameGlobal = document.getElementById('user-list').dataset.currentUser;

        if (!peerConnection) { // If called, PC might not exist yet.
            // This implies the callee accepted the call UI prompt, started local media, then created PC.
            // This logic might need adjustment if PC is created earlier for callee.
            // For now, assume acceptCallButton click handler already called startLocalMedia() and createPeerConnection().
            // If it's the caller receiving their own offer (not typical), ignore.
             if (data.caller_username === myUsernameGlobal) return;
        }
        
        // Callee path: Accept button should have been clicked, local media started, PC created.
        if (!localStream || !peerConnection) {
            console.warn("Received offer but local media/peer connection not ready. Callee should accept first.");
            // Potentially, cache the offer if UI flow allows accepting then media setup.
            // For now, assume callee clicks "Accept", then media starts, then PC is made, then offer is processed.
            // This means 'acceptCallButton' should not directly send an 'answer_pending' or similar.
            // It should just prepare for the offer.
            callStatus.textContent = "Offer received. Please ensure you've accepted the call and allowed media.";
            // To handle this robustly, cache the offer if `peerConnection` is not ready.
            // For now, we assume `acceptCallButton` has been clicked and `createPeerConnection` called.
            if (!peerConnection) {
                 console.log("PeerConnection not ready for offer. Callee must accept call first.");
                 // Store offer to be processed after PC is ready
                 // window.pendingOffer = data.sdp; return;
                 // For now, this path assumes acceptCallButton prepares PC
                  if (!await startLocalMedia()) { closeVideoCall(); return; }
                  createPeerConnection();
            }
        }

        try {
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
            console.log('Remote description (offer) set.');
            
            // If this client is the callee, now create and send an answer
            if (data.caller_username !== myUsernameGlobal) { // We are the callee
                const answer = await peerConnection.createAnswer();
                await peerConnection.setLocalDescription(answer);
                console.log('Answer created and local description set. Emitting answer_sdp.');
                socket.emit('answer_sdp', { 
                    'target_username': data.caller_username, // Send back to original caller
                    'callee_username': myUsernameGlobal,
                    'sdp': answer 
                });
                callStatus.textContent = 'Answer sent.';
                videoCallUI.style.display = 'block'; // Ensure UI is visible
            }
        } catch (error) {
            console.error('Error handling received SDP offer:', error);
            callStatus.textContent = 'Error processing call offer.';
        }
    });

    socket.on('answer_sdp_received', async (data) => {
        // data: {'sdp': answer, 'callee_username': 'UserB'}
        console.log('Answer SDP received from', data.callee_username);
        // This client is the original caller.
        if (!peerConnection) {
            console.error('Received answer but no peer connection exists.');
            return;
        }
        try {
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
            console.log('Remote description (answer) set.');
            callStatus.textContent = 'Call connected!';
            videoCallUI.style.display = 'block'; // Ensure UI is visible
        } catch (error) {
            console.error('Error handling received SDP answer:', error);
            callStatus.textContent = 'Error processing call answer.';
        }
    });

    socket.on('ice_candidate_received', async (data) => {
        // data: {'candidate': candidate, 'sender_username': 'UserX'}
        console.log('ICE candidate received from', data.sender_username);
        if (!peerConnection) {
            console.error('Received ICE candidate but no peer connection exists.');
            return;
        }
        try {
            await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
            console.log('ICE candidate added.');
        } catch (error) {
            console.error('Error adding received ICE candidate:', error);
        }
    });

    socket.on('call_hanged_up', (data) => {
        // data: {'sender_username': 'UserX'}
        console.log('Call hanged up by', data.sender_username);
        callStatus.textContent = `Call ended by ${data.sender_username}.`;
        closeVideoCall();
    });
    
    socket.on('call_rejected_by_peer', (data) => {
        // data: {'callee_username': 'UserX'}
        console.log('Call rejected by', data.callee_username);
        callStatus.textContent = `Call rejected by ${data.callee_username}.`;
        closeVideoCall();
    });

    // Ensure `myUsernameGlobal` is set when the page loads if the user is known
    // This might be better passed from the template or set after login
    const currentUserData = document.getElementById('user-list');
    if (currentUserData && currentUserData.dataset.currentUser) {
        myUsernameGlobal = currentUserData.dataset.currentUser;
    } else {
        console.warn("Could not determine current user's username for video calls.");
        // Fallback or prompt if necessary
    }


    console.log('Video call script loaded and signaling handlers attached.');
});

const socket = io();
const peer = new Peer();

let localStream;

navigator.mediaDevices.getUserMedia({ video: true, audio: true })
    .then(stream => {
        localStream = stream;
        document.getElementById('localVideo').srcObject = stream;
    }).catch(err => console.error('Error accessing media devices:', err));

peer.on('open', id => {
    console.log('My peer ID is: ' + id);
    socket.emit('start_chat', { peer_id: id });
});

socket.on('chat_started', data => {
    document.getElementById('chatStatus').innerText = `Chatting with ${data.user}`;
    const call = peer.call(data.peer_id, localStream);
    call.on('stream', remoteStream => {
        document.getElementById('remoteVideo').srcObject = remoteStream;
    });
});

peer.on('call', call => {
    call.answer(localStream);
    call.on('stream', remoteStream => {
        document.getElementById('remoteVideo').srcObject = remoteStream;
    });
});

socket.on('gift_received', data => {
    alert(`Received ${data.gift} from ${data.from}`);
});

document.getElementById('startChat').addEventListener('click', () => {
    socket.emit('start_chat', { peer_id: peer.id });
});

function sendGift(giftId, recipientId) {
    socket.emit('send_gift', { gift_id: giftId, recipient_id: recipientId });
}
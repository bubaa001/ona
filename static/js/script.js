const socket = io();

navigator.mediaDevices.getUserMedia({ video: true, audio: true })
    .then(stream => {
        document.getElementById('localVideo').srcObject = stream;
    });

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('chat_started', (data) => {
    document.getElementById('chatStatus').innerText = `Chatting with ${data.user}`;
    // Add WebRTC peer connection logic here
});

socket.on('gift_received', (data) => {
    alert(`Received ${data.gift} from ${data.from}`);
});

document.getElementById('startChat').addEventListener('click', () => {
    socket.emit('start_chat');
});

function sendGift(giftId) {
    socket.emit('send_gift', { gift_id: giftId, recipient_id: 1 }); // Replace recipient_id dynamically
}
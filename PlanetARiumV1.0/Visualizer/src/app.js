const express = require('express');
const app = express();
const http = require('http').Server(app);
const io = require('socket.io')(http);

app.use(require('./routes/streamingvideo.routes'));

app.use(express.static(__dirname + "/public"));

app.use(
    express.urlencoded({
        extended: true
    })
)

app.use(express.json())

io.on('connection', (socket) => {
    socket.on('frame', (image) => {
        socket.broadcast.emit('stream', image.toString('base64'));
    });

    socket.on('blobs', (data) => {
        socket.broadcast.emit('blobs', data);
    });

    socket.on('aruco', (data) => {
        socket.broadcast.emit('aruco', data);
    });

    socket.on('qr', (data) => {
        socket.broadcast.emit('qr', data);
    });

    socket.on('server', (data) => {
        socket.broadcast.emit('server', data)
    });
})

module.exports = http;
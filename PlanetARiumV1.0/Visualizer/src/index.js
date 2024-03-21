const http = require('./app');
const port = process.env.FRAME_PORT || 8100;


http.listen(port, () => {
    console.log('Server in port ' + port.toString());
});

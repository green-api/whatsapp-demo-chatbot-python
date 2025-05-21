const { default: makeWASocket, useSingleFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const { join } = require('path');

const { state, saveState } = useSingleFileAuthState('./auth_info.json');

async function startSocket() {
    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: true, // THIS SHOWS QR
    });

    sock.ev.on('creds.update', saveState);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect } = update;
        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect.error = Boom)?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log('connection closed due to', lastDisconnect.error, ', reconnecting', shouldReconnect);
            if (shouldReconnect) {
                startSocket();
            }
        } else if (connection === 'open') {
            console.log('✅ Bot connected');
        }
    });

    return sock;
}

startSocket();

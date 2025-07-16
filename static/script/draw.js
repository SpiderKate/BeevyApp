const canvas = document.getElementById('drawCanvas');
        const ctx = canvas.getContext('2d');
        const socket = io();  // connect to WebSocket

        let drawing = false;

        canvas.addEventListener('mousedown', () => drawing = true);
        canvas.addEventListener('mouseup', () => drawing = false);
        canvas.addEventListener('mousemove', (e) => {
            if (!drawing) return;
            const x = e.offsetX;
            const y = e.offsetY;
            socket.emit('draw', {x, y});
            draw(x, y);
        });

        socket.on('draw', ({x, y}) => draw(x, y));

        function draw(x, y) {
            ctx.fillStyle = 'black';
            ctx.fillRect(x, y, 2, 2);
        }
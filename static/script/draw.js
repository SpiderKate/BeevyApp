const canvas = document.getElementById('drawCanvas');
        const ctx = canvas.getContext('2d');
        const socket = io();  //pripoji se k WebSocket

        let drawing = false;
        let lastX = 0;
        let lastY = 0;

        canvas.addEventListener('mousedown', (e) =>{
            drawing = true;
            lastX = e.offsetX;
            lastY = e.offsetY;
        });
        canvas.addEventListener('mouseup', () => drawing = false);
        canvas.addEventListener('mousemove', (e) => {
            if (!drawing) return;
            const x = e.offsetX;
            const y = e.offsetY;
            socket.emit('draw', {fromX: lastX, fromY: lastY, toX: x, toY: y});
            draw(lastX, lastY, x, y);
            lastX = x;
            lastY = y;
        });

        socket.on('draw', ({fromX, fromY, toX, toY}) => {
            draw(fromX, fromY, toX, toY);
        });
        function draw(fromX, fromY, toX, toY) {
            ctx.strokeStyle = 'black';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(fromX, fromY);
            ctx.lineTo(toX, toY);
            ctx.stroke();
        }
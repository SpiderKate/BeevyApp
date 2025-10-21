const canvas = document.getElementById('drawCanvas');
const ctx = canvas.getContext('2d');
const room_ID = canvas.dataset.roomId;
const socket = io();  //pripoji se k WebSocket
//const socket = io("https://c85432c98e12.ngrok-free.app");  //pripoji se k WebSocket pres ngrok
socket.emit('join_room', { room: room_ID });

//posila drawdata na server
function sendDrawData(drawData) {
    socket.emit('draw', { room: room_ID, ...drawData });
}

let drawing = false;
let lastX = 0;
let lastY = 0;
let currentColor = '#000';
let slider = document.getElementById("sizeSlider");
let brushSize

//odposlouchava slider a meni velikost stetce
slider.addEventListener("change", (e)=>{brushSize=e.target.value
    console.log(brushSize);
});
//mopuse events
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
    let brushSize = slider.value;
    sendDrawData({fromX: lastX, fromY: lastY, toX: x, toY: y, color: currentColor, width: brushSize});
    draw(lastX, lastY, x, y, currentColor, brushSize);
    lastX = x;
    lastY = y;
});


//styl kresby
function draw(fromX, fromY, toX, toY, color, width) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(fromX, fromY);
    ctx.lineTo(toX, toY);
    ctx.stroke();
}

const colorPicker = new iro.ColorPicker("#colorPicker", { //vytvori novy color picker
    width: 150,
    color: "#000" //default barva
});
//posila historii mistnosti pro nove pripojene uzivatele
socket.on('draw_history', (history) => {
    history.forEach(({fromX, fromY, toX, toY, color, width}) => {
        draw(fromX, fromY, toX, toY, color, width);
    });
});

//prijima data od ostatnich uzivatelu
socket.on('draw', ({fromX, fromY, toX, toY, color, width}) => {
    draw(fromX, fromY, toX, toY, color, width);
}); 
//meni barvu podle vyberu na color pickeru
colorPicker.on('color:change', function(color) {
    currentColor = color.hexString;
});
const canvas = document.getElementById('drawCanvas');
toolBtns = document.querySelectorAll(".tool");
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
let brushSize;
let slider = document.getElementById("sizeSlider");
let clearcanvas = document.getElementById("clearCanvas");
let fillColor = document.getElementById("fillColor");
let canvasSnapshot = null;


//odposlouchava slider a meni velikost stetce
slider.addEventListener("change", (e)=>{brushSize=e.target.value
    console.log(brushSize);
    document.getElementById("size").innerHTML=brushSize;

});

let currentTool = "brush";

toolBtns.forEach(btn => {
    btn.addEventListener("click", () => {
        currentTool = btn.id; // ulozi aktivni nastroj
        console.log("Selected tool:", currentTool);
    });
});

canvas.addEventListener("mousedown", (e) => {
    drawing = true;
    lastX = e.offsetX;
    lastY = e.offsetY;

    if (currentTool === "rectangle" || currentTool === "triangle") {
        saveCanvasState();
    }
});

canvas.addEventListener("mouseup", (e) => {
    if (currentTool === "rectangle") {
        restoreCanvasState();
        rectangle(lastX, lastY, e.offsetX, e.offsetY, currentColor, brushSize);
    }
    else if (currentTool === "triangle") {
        triangle(lastX, lastY, e.offsetX, e.offsetY, currentColor, brushSize);
    }
    drawing = false;
});

canvas.addEventListener("mousemove", (e) => {
    if (!drawing) return;

    let x = e.offsetX;
    let y = e.offsetY;
    let brushSize = slider.value;

    if (currentTool === "brush") {
        x = e.offsetX;
        y = e.offsetY;
        sendDrawData({ fromX: lastX, fromY: lastY, toX: x, toY: y, color: currentColor, width: brushSize });
        draw(lastX, lastY, x, y, currentColor, brushSize);
        lastX = x;
        lastY = y;
    }
    else if (currentTool === "eraser") {
        x = e.offsetX;
        y = e.offsetY;
        lastX = x;
        lastY = y;
        
        sendDrawData({ fromX: lastX, fromY: lastY, toX: x, toY: y, color: "#ffffff", width: brushSize });
        draw(lastX, lastY, x, y, "#ffffff", brushSize);
    }
    else if (currentTool === "rectangle") {
        restoreCanvasState();
        rectangle(lastX, lastY, x, y, currentColor, brushSize);
    }
    else if (currentTool === "triangle") {
        restoreCanvasState();
        triangle(lastX, lastY, x, y, currentColor, brushSize);
    }
    else if (currentTool === "brush" || currentTool === "eraser") {
        lastX = x;
        lastY = y;
    }
    
    if (currentTool === "circle") {
        restoreCanvasState();
        circle(lastX, lastY, x, y, currentColor, brushSize);
    }
    
});

function saveCanvasState() {
    canvasSnapshot = ctx.getImageData(0, 0, canvas.width, canvas.height);
}

function restoreCanvasState() {
    if (canvasSnapshot) {
        ctx.putImageData(canvasSnapshot, 0, 0);
    }
}


//styl kresby
function draw(fromX, fromY, toX, toY, color, width) {
    ctx.strokeStyle = color; //kresli/vyplnuje line barvou 
    ctx.lineWidth = width;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(fromX, fromY);
    ctx.lineTo(toX, toY); //tvori line pomoci mouse event
    ctx.stroke();
}

function rectangle(fromX, fromY, toX, toY, color, width) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;

    const rectX = Math.min(fromX, toX);
    const rectY = Math.min(fromY, toY);
    const rectW = Math.abs(toX - fromX);
    const rectH = Math.abs(toY - fromY);

    ctx.beginPath();
    ctx.rect(rectX, rectY, rectW, rectH);
    ctx.stroke();
};

function triangle(fromX, fromY, toX, toY, color, width) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    const triW = Math.abs(toX - fromX);
    const triH = Math.abs(toY - fromY);
//chyba!!
    ctx.beginPath();
    ctx.moveTo(fromX,fromY);
    ctx.lineTo(toX,toY);
    if(toY<fromY || toX < fromX){
        ctx.lineTo(toX+triW,toY-triH);
    }
    else if (fromY<toY || toX > fromX) {
        ctx.lineTo(toX+triW,toY+triH)
    }
    ctx.stroke();
};

function circle(){
    console.log("weeeee");
};

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
    currentColor=color.hexString;
});


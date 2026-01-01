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

function resizeCanvas() {
    // save current drawing
    const temp = ctx.getImageData(0, 0, canvas.width, canvas.height);

    // set canvas width and height to match its CSS size
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    // restore previous drawing
    ctx.putImageData(temp, 0, 0);
}

// call on page load
resizeCanvas();

// call on window resize
window.addEventListener('resize', resizeCanvas);

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
        //currentTool.classList.add('active');
        //!currentTool.classList.remove('active')
    });
});

canvas.addEventListener("mousedown", (e) => {
    drawing = true;
    lastX = e.offsetX;
    lastY = e.offsetY;

    if (currentTool === "rectangle" || currentTool === "triangle" || currentTool === "circle") {
        saveCanvasState();
    }
});

canvas.addEventListener("mouseup", (e) => {
    const data = { 
            fromX: lastX,
            fromY: lastY,
            toX: e.offsetX,
            toY: e.offsetY,
            color: currentColor,
            width: brushSize
        };
    if (currentTool === "rectangle") {
        restoreCanvasState();
        sendDrawData({ type:"rect", ...data});
        rectangle(data);
    }
    else if (currentTool === "triangle") {
        restoreCanvasState();
        sendDrawData({ type:"tri", ...data});
        triangle(data);
    }
    else if (currentTool === "circle") {
        restoreCanvasState();
        sendDrawData({ type:"circ", ...data});
        circle(data);
    }
    drawing = false;
});

canvas.addEventListener("mousemove", (e) => {
    if (!drawing) return;

    let x = e.offsetX;
    let y = e.offsetY;
    let brushSize = slider.value;
    
    if (currentTool === "brush") {
        const data = { 
            fromX: lastX,
            fromY: lastY,
            toX: e.offsetX,
            toY: e.offsetY,
            color: currentColor,
            width: brushSize
        };
        x = e.offsetX;
        y = e.offsetY;
        sendDrawData({ type:"line", ...data});
        draw(data);
        lastX = x;
        lastY = y;
    }
    else if (currentTool === "eraser") {
         const data = { 
            fromX: lastX,
            fromY: lastY,
            toX: e.offsetX,
            toY: e.offsetY,
            color: '#ffffff',
            width: brushSize
        };
        x = e.offsetX;
        y = e.offsetY;
        sendDrawData({ type:"line",  ...data});
        draw(data);
        lastX = x;
        lastY = y;      
    }
    else if (currentTool === "rectangle") {
        restoreCanvasState();
        const data = { 
            fromX: lastX,
            fromY: lastY,
            toX: x,
            toY: y,
            color: currentColor,
            width: brushSize
        };
        rectangle(data);
    }
    else if (currentTool === "triangle") {
        restoreCanvasState();
        const data = { 
            fromX: lastX,
            fromY: lastY,
            toX: x,
            toY: y,
            color: currentColor,
            width: brushSize
        };
        triangle(data);
    }
    if (currentTool === "circle") {
        restoreCanvasState();
        const data = { 
            fromX: lastX,
            fromY: lastY,
            toX: x,
            toY: y,
            color: currentColor,
            width: brushSize
        };
        circle(data);
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
function draw(data) {
    ctx.strokeStyle = data.color; //kresli/vyplnuje line barvou 
    ctx.lineWidth = data.width;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(data.fromX, data.fromY);
    ctx.lineTo(data.toX, data.toY); //tvori line pomoci mouse event
    ctx.stroke();
}

function rectangle(data) {
    ctx.strokeStyle = data.color;
    ctx.lineWidth = data.width;

    const rectX = Math.min(data.fromX, data.toX);
    const rectY = Math.min(data.fromY, data.toY);
    const rectW = Math.abs(data.toX - data.fromX);
    const rectH = Math.abs(data.toY - data.fromY);

    ctx.beginPath();
    ctx.rect(rectX, rectY, rectW, rectH);
    ctx.stroke();
};

function triangle(data) {
    const { fromX, fromY, toX, toY, color, width } = data;
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    const triW = Math.abs(toX - fromX);
    const triH = Math.abs(toY - fromY);
    ctx.beginPath();
    ctx.moveTo(fromX,fromY);
    ctx.lineTo(toX,toY);
    if(fromY>toY && fromX<toX){
        ctx.lineTo(toX+triW,toY+triH);
        ctx.moveTo(fromX,fromY);
        ctx.lineTo(toX+triW,fromY);
    }
    else if (fromY<toY && fromX<toX) {
        ctx.lineTo(toX+triW,toY-triH);
        ctx.moveTo(fromX,fromY);
        ctx.lineTo(toX+triW,fromY);
    }
    else if (fromY>toY && fromX>toX) {
        ctx.lineTo(toX-triW,toY+triH);
        ctx.moveTo(fromX,fromY);
        ctx.lineTo(toX-triW,fromY);
    }
    else if (fromY<toY && fromX>toX) {
        ctx.lineTo(toX-triW,toY-triH);
        ctx.moveTo(fromX,fromY);
        ctx.lineTo(toX-triW,fromY);
    }
    ctx.closePath();
    ctx.stroke();
};

function circle(data){
    const { fromX, fromY, toX, toY, color, width } = data;
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    a = Math.abs(toX-fromX);
    b = Math.abs(toY-fromY);
    c = Math.sqrt(a*a + b*b);
    ctx.beginPath();
    ctx.arc(fromX, fromY, c, 0, 2 * Math.PI);
    ctx.stroke();
};

const colorPicker = new iro.ColorPicker("#colorPicker", { //vytvori novy color picker
    width: 150,
    color: "#000" //default barva
});

//posila historii mistnosti pro nove pripojene uzivatele
socket.on('draw_history', (history) => {
    history.forEach((data) => {
        switch (data.type){
        case "line": draw(data);
        break;
        case "rect": rectangle(data);
        break;
        case "tri": triangle(data);
        break;
        case "circ": circle(data);
        break;
    }
    });
});

//prijima data od ostatnich uzivatelu
socket.on('draw', (data) => {
    switch (data.type){
        case "line": draw(data);
        break;
        case "rect": rectangle(data);
        break;
        case "tri": triangle(data);
        break;
        case "circ": circle(data);
        break;
    }
}); 
//meni barvu podle vyberu na color pickeru
colorPicker.on('color:change', function(color) {
    currentColor=color.hexString;
});


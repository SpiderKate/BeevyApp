document.addEventListener("DOMContentLoaded", () => {
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

function showTool(name) {
    document.querySelectorAll('.tool').forEach(t => t.classList.remove('active'));
    document.getElementById(name).classList.add('active');
}

const BASE_WIDTH = 1600;
const BASE_HEIGHT = 1200;

function getNormalizedPos(e) {
    const rect = canvas.getBoundingClientRect();
    return {
        x: (e.clientX - rect.left) / rect.width,
        y: (e.clientY - rect.top) / rect.height
    };
}

function denormX(x) {
    return x * canvas.width;
}

function denormY(y) {
    return y * canvas.height;
}

function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();

    canvas.width = BASE_WIDTH;
    canvas.height = BASE_HEIGHT;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();

let drawing = false;
let lastX = 0;
let lastY = 0;
let currentColor = '#000';
let brushSize = document.getElementById("size").value;
let slider = document.getElementById("sizeSlider");
let clearcanvas = document.getElementById("clearCanvas");
let canvasSnapshot = null;

clearcanvas.addEventListener("click", () => { // Clear locally 
    ctx.clearRect(0, 0, canvas.width, canvas.height); // Sync to others 
    sendDrawData({ type: "clear" }); 
});

//odposlouchava slider a meni velikost stetce
slider.addEventListener("input", (e)=>{brushSize=e.target.value
    document.getElementById("size").innerHTML=brushSize;

});

let currentTool = "brush";

toolBtns.forEach(btn => {
    btn.addEventListener("click", () => {
        currentTool = btn.id; // ulozi aktivni nastroj
        console.log("Selected tool:", currentTool);
        showTool(btn.id);
        //currentTool.classList.add('active');
        //!currentTool.classList.remove('active')
    });
});

canvas.addEventListener("mousedown", (e) => {
    const pos = getNormalizedPos(e);
    if (currentTool === "bucket") { 
        const data = {
            x: pos.x, y: pos.y, color: currentColor 
        }; // local fill 
        bucketFillAtNormalized(data); // sync to others 
        sendDrawData({ type: "bucket", ...data }); 
        return; 
    }
    drawing = true;
    
    lastX = pos.x;
    lastY = pos.y;

    if (currentTool === "rectangle" || currentTool === "triangle" || currentTool === "circle") {
        saveCanvasState();
    }
});

canvas.addEventListener("mouseup", (e) => {
    const pos = getNormalizedPos(e);
    const data = { 
            fromX: lastX,
            fromY: lastY,
            toX: pos.x,
            toY: pos.y,
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
    const pos = getNormalizedPos(e);
    
    if (currentTool === "brush") {
        const data = { 
            fromX: lastX,
            fromY: lastY,
            toX: pos.x,
            toY: pos.y,
            color: currentColor,
            width: slider.value
        };
        sendDrawData({ type: "line", ...data });
        draw(data);

        lastX = pos.x;
        lastY = pos.y;
    }
    else if (currentTool === "eraser") {
        const data = { 
            fromX: lastX,
            fromY: lastY,
            toX: pos.x,
            toY: pos.y,
            color: '#ffffff',
            width: brushSize
        };
        sendDrawData({ type:"line",  ...data});
        draw(data);

        lastX = pos.x;
        lastY = pos.y;      
    }
    else if (currentTool === "rectangle") {
        restoreCanvasState();
        const data = { 
            fromX: lastX,
            fromY: lastY,
            toX: pos.x,
            toY: pos.y,
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
            toX: pos.x,
            toY: pos.y,
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
            toX: pos.x,
            toY: pos.y,
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
    ctx.lineWidth = data.width * (canvas.width / BASE_WIDTH);
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(denormX(data.fromX), denormY(data.fromY));
    ctx.lineTo(denormX(data.toX), denormY(data.toY));
    ctx.stroke();
}

function rectangle(data) {
    ctx.strokeStyle = data.color;
    ctx.lineWidth = data.width * (canvas.width / BASE_WIDTH);
    const x1 = denormX(data.fromX);
    const y1 = denormY(data.fromY);
    const x2 = denormX(data.toX);
    const y2 = denormY(data.toY);

    const rectX = Math.min(x1, x2);
    const rectY = Math.min(y1, y2);
    const rectW = Math.abs(x2 - x1);
    const rectH = Math.abs(y2 - y1);

    ctx.beginPath();
    ctx.rect(rectX, rectY, rectW, rectH);
    ctx.stroke();
};

function triangle(data) {
    const { fromX, fromY, toX, toY, color, width } = data;
    ctx.strokeStyle = color;
    ctx.lineWidth = data.width * (canvas.width / BASE_WIDTH);
    const x1 = denormX(fromX);
    const y1 = denormY(fromY);
    const x2 = denormX(toX);
    const y2 = denormY(toY);

    const triW = Math.abs(x2 - x1);
    const triH = Math.abs(y2 - y1);
    ctx.beginPath();
    ctx.moveTo(x1,y1);
    ctx.lineTo(x2,y2);
    if(y1>y2 && x1<x2){
        ctx.lineTo(x2+triW,y2+triH);
        ctx.moveTo(x1,y1);
        ctx.lineTo(x2+triW,y1);
    }
    else if (y1<y2 && x1<x2) {
        ctx.lineTo(x2+triW,y2-triH);
        ctx.moveTo(x1,y1);
        ctx.lineTo(x2+triW,y1);
    }
    else if (y1>y2 && x1>x2) {
        ctx.lineTo(x2-triW,y2+triH);
        ctx.moveTo(x1,y1);
        ctx.lineTo(x2-triW,y1);
    }
    else if (y1<y2 && x1>x2) {
        ctx.lineTo(x2-triW,y2-triH);
        ctx.moveTo(x1,y1);
        ctx.lineTo(x2-triW,y1);
    }
    ctx.closePath();
    ctx.stroke();
};

function circle(data){
    const { fromX, fromY, toX, toY, color, width } = data;
    ctx.strokeStyle = color;
    ctx.lineWidth = data.width * (canvas.width / BASE_WIDTH);
    const x1 = denormX(fromX);
    const y1 = denormY(fromY);
    const x2 = denormX(toX);
    const y2 = denormY(toY);

    const a = x2 - x1;
    const b = y2 - y1;
    const c = Math.sqrt(a*a + b*b);

    ctx.beginPath();
    ctx.arc(x1, y1, c, 0, 2 * Math.PI);
    ctx.stroke();
};

function bucketFillAtNormalized(data) { 
    const x = Math.floor(denormX(data.x)); 
    const y = Math.floor(denormY(data.y)); 
    bucketFill(canvas, x, y, data.color); 
} 

function bucketFill(canvas, x, y, fillColor, tolerance = 0) {
    const ctx = canvas.getContext("2d"); 
    const width = canvas.width; 
    const height = canvas.height; 
    const imgData = ctx.getImageData(0, 0, width, height); 
    const data = imgData.data; 
    const startPos = (y * width + x) * 4; 
    const targetColor = [ 
        data[startPos], 
        data[startPos + 1], 
        data[startPos + 2], 
        data[startPos + 3] 
    ]; 
    const newColor = hexToRgba(fillColor); 
    if (colorsMatch(targetColor, newColor)) 
        return; 
    const stack = [[x, y]]; 
    while (stack.length) { 
        const [cx, cy] = stack.pop(); 
        if (cx < 0 || cy < 0 || cx >= width || cy >= height) continue; 
        const pos = (cy * width + cx) * 4; 
        const current = [ 
            data[pos], 
            data[pos + 1], 
            data[pos + 2], 
            data[pos + 3] 
        ]; 
        if (!colorsMatch(current, targetColor, tolerance)) continue; 
        data[pos] = newColor[0]; 
        data[pos + 1] = newColor[1]; 
        data[pos + 2] = newColor[2]; 
        data[pos + 3] = newColor[3]; 
        stack.push([cx + 1, cy]); 
        stack.push([cx - 1, cy]); 
        stack.push([cx, cy + 1]); 
        stack.push([cx, cy - 1]); 
    } ctx.putImageData(imgData, 0, 0); 
} 

function colorsMatch(a, b, tolerance = 0) { return ( 
    Math.abs(a[0] - b[0]) <= tolerance && 
    Math.abs(a[1] - b[1]) <= tolerance && 
    Math.abs(a[2] - b[2]) <= tolerance && 
    Math.abs(a[3] - b[3]) <= tolerance ); 

} function hexToRgba(hex) { 
    hex = hex.replace("#", ""); 
    const bigint = parseInt(hex, 16); 
    return [ 
        (bigint >> 16) & 255, 
        (bigint >> 8) & 255, 
        bigint & 255, 
        255 
    ]; 
}

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
        case "bucket": bucketFillAtNormalized(data); 
        break;
        case "clear": ctx.clearRect(0, 0, canvas.width, canvas.height); 
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
        case "bucket": bucketFillAtNormalized(data); 
        break;
        case "clear": ctx.clearRect(0, 0, canvas.width, canvas.height); 
        break;
    }
}); 
//meni barvu podle vyberu na color pickeru
colorPicker.on('color:change', function(color) {
    currentColor=color.hexString;
});


const saveImg = document.getElementById("saveImg").
addEventListener("click", ()=>{
    const dataURL = canvas.toDataURL("image/png");
    const link = document.createElement("a");
    const filename = prompt("Name your drawing","myDrawing");
    if(!filename) return;
    link.href = dataURL;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
})  
});

// TODO: users history on the canvas so undo can work for the user and not the canvas
// TODO: layers
// TODO: cursors with mini pfp or universal icon is visible to everyone

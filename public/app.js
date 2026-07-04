// Replace your current static/app.js file entirely with this version
const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
const wsUrl = `${wsProtocol}${window.location.host}/ws`;
const socket = new WebSocket(wsUrl);

let mySymbol = null;
let myRole = null; 
let currentTurn = "X";
let gameActive = true;

const statusDiv = document.getElementById("status");
const cells = document.querySelectorAll(".cell");
const choiceModal = document.getElementById("choice-modal");

const taskModal = document.getElementById("task-modal");
const taskTitle = document.getElementById("task-title");
const taskDesc = document.getElementById("task-desc");
const winnerInputArea = document.getElementById("winner-input-area");
const loserReadArea = document.getElementById("loser-read-area");
const assignedTaskText = document.getElementById("assigned-task");
const modalCloseBtn = document.getElementById("modal-close-btn");

socket.onmessage = (event) => {
    let data;
    
    // SAFE PARSING: Prevents the "Expected a JSON object" crash if non-JSON data arrives
    try {
        data = JSON.parse(event.data);
    } catch (error) {
        console.warn("Received a non-JSON payload from server:", event.data);
        return; 
    }

    if (data.error) {
        statusDiv.innerText = data.error;
        return;
    }

    if (data.role) { myRole = data.role; }

    if (data.symbol) {
        mySymbol = data.symbol;
        choiceModal.style.display = "none"; 
    }

    if (data.board) {
        currentTurn = data.turn;
        
        cells.forEach((cell, index) => {
            cell.innerText = data.board[index];
        });

        if (data.players_count < 2) {
            statusDiv.innerText = "Waiting for Friend to join...";
            choiceModal.style.display = "none";
            taskModal.style.display = "none";
        } else if (!data.choices_set) {
            if (myRole === "player1") {
                statusDiv.innerText = "Choose your symbol!";
                choiceModal.style.display = "flex"; 
            } else {
                statusDiv.innerText = "Waiting for Player 1 to pick X/O...";
                choiceModal.style.display = "none";  
            }
        } else if (data.winner) {
            gameActive = false;
            choiceModal.style.display = "none"; 
            
            if (data.winner === "Draw") {
                statusDiv.innerText = "It's a Draw! 👔";
            } else {
                statusDiv.innerText = data.winner === mySymbol ? "You Win! 🎉" : "Friend Wins! 🤖";
                taskModal.style.display = "flex";
                
                if (data.winner === mySymbol) {
                    // WINNER VIEW CODE
                    taskTitle.innerText = "Victory! 🏆";
                    winnerInputArea.style.display = "block";
                    loserReadArea.style.display = "none";
                    
                    if (!data.task) {
                        taskDesc.innerText = "Type a penalty task/gift for your friend:";
                        document.getElementById("winner-view-ack").innerText = "";
                    } else {
                        taskDesc.innerText = "Penalty successfully delivered!";
                        // Display the loser's reply if they sent one
                        if (data.ack) {
                            document.getElementById("winner-view-ack").innerText = `Friend's Reply: "${data.ack}"`;
                            modalCloseBtn.style.display = "inline-block";
                        } else {
                            document.getElementById("winner-view-ack").innerText = "Waiting for their reaction...";
                        }
                    }
                } else {
                    // LOSER VIEW CODE
                    taskTitle.innerText = "Defeat! 💀";
                    winnerInputArea.style.display = "none";
                    loserReadArea.style.display = "block";
                    
                    if (data.task) {
                        taskDesc.innerText = "Your punishment has arrived!";
                        assignedTaskText.innerText = `YOUR TASK: ${data.task}`;
                        
                        if (!data.ack) {
                            document.getElementById("loser-ack-input-area").style.display = "block";
                            modalCloseBtn.style.display = "none";
                        } else {
                            document.getElementById("loser-ack-input-area").style.display = "none";
                            taskDesc.innerText = "Reaction sent to your friend!";
                            modalCloseBtn.style.display = "inline-block";
                        }
                    } else {
                        taskDesc.innerText = "Your friend is choosing your punishment...";
                        assignedTaskText.innerText = "Waiting for them to type...";
                        document.getElementById("loser-ack-input-area").style.display = "none";
                        modalCloseBtn.style.display = "none";
                    }
                }
            }
        } else {
            // Cleanup on Reset
            gameActive = true;
            statusDiv.innerText = currentTurn === mySymbol ? `Your Turn (${mySymbol})` : `Friend's Turn (${currentTurn})`;
            taskModal.style.display = "none";
            choiceModal.style.display = "none"; 
            document.getElementById("task-input").value = "";
            document.getElementById("ack-input").value = "";
        }
    }
};

function pickSymbol(symbol) {
    if (myRole === "player1") {
        socket.send(JSON.stringify({ type: "choose_symbol", symbol: symbol }));
    }
}

function submitTask() {
    const taskText = document.getElementById("task-input").value;
    if (taskText.trim() !== "") {
        socket.send(JSON.stringify({ type: "send_task", task: taskText }));
    }
}

// Send acknowledgment string to server
function submitAck() {
    const ackText = document.getElementById("ack-input").value;
    if (ackText.trim() !== "") {
        socket.send(JSON.stringify({ type: "send_ack", ack: ackText }));
    }
}

function closeTaskModal() {
    taskModal.style.display = "none";
}

cells.forEach(cell => {
    cell.addEventListener("click", () => {
        const index = cell.getAttribute("data-index");
        if (gameActive && currentTurn === mySymbol && cell.innerText === "") {
            socket.send(JSON.stringify({ type: "move", index: parseInt(index), symbol: mySymbol }));
        }
    });
});

document.getElementById("reset-btn").addEventListener("click", () => {
    socket.send(JSON.stringify({ type: "reset" }));
});
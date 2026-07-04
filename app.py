from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

def check_winner(board):
    wins = [
        [0,1,2], [3,4,5], [6,7,8],
        [0,3,6], [1,4,7], [2,5,8],
        [0,4,8], [2,4,6]
    ]
    for combo in wins:
        if board[combo[0]] and board[combo[0]] == board[combo[1]] == board[combo[2]]:
            return board[combo[0]]
    if "" not in board:
        return "Draw"
    return None

class Game:
    def __init__(self):
        self.board = [""] * 9
        self.turn = "X"
        self.player_connections = [] 
        self.player_symbols = {}     
        self.p1_choice = None
        self.winner = None
        self.task = None
        self.ack = None # NEW: Tracks the loser's acknowledgment message

game = Game()

async def broadcast_state():
    state = json.dumps({
        "board": game.board,
        "turn": game.turn,
        "players_count": len(game.player_connections),
        "winner": game.winner,
        "choices_set": game.p1_choice is not None,
        "task": game.task,
        "ack": game.ack # Send ACK status to everyone
    })
    for player in game.player_connections:
        await player.send_text(state)

@app.get("/")
def get_index():
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    if len(game.player_connections) >= 2:
        await websocket.send_json({"error": "Game Full"})
        await websocket.close()
        return

    game.player_connections.append(websocket)
    is_player1 = (game.player_connections[0] == websocket)
    
    if is_player1:
        await websocket.send_json({"role": "player1"})
    else:
        await websocket.send_json({"role": "player2"})
        if game.p1_choice is not None:
            p2_symbol = "O" if game.p1_choice == "X" else "X"
            game.player_symbols[websocket] = p2_symbol
            await websocket.send_json({"symbol": p2_symbol})
    
    await broadcast_state()

    try:
        while True:
            data = await websocket.receive_text()
            event = json.loads(data)
            
            if event["type"] == "choose_symbol" and game.p1_choice is None:
                if game.player_connections[0] == websocket:
                    choice = event["symbol"]
                    game.p1_choice = choice
                    game.player_symbols[websocket] = choice
                    await websocket.send_json({"symbol": choice})
                    
                    if len(game.player_connections) == 2:
                        p2_ws = game.player_connections[1]
                        p2_symbol = "O" if choice == "X" else "X"
                        game.player_symbols[p2_ws] = p2_symbol
                        await p2_ws.send_json({"symbol": p2_symbol})
                    
                    await broadcast_state()

            elif event["type"] == "move":
                user_symbol = game.player_symbols.get(websocket)
                if game.winner is None and game.board[event["index"]] == "" and user_symbol == game.turn:
                    game.board[event["index"]] = game.turn
                    game.winner = check_winner(game.board)
                    if not game.winner:
                        game.turn = "O" if game.turn == "X" else "X"
                    await broadcast_state()
            
            elif event["type"] == "send_task":
                if game.winner and game.player_symbols.get(websocket) == game.winner:
                    game.task = event["task"]
                    await broadcast_state()

            # NEW: Handle loser submitting an acknowledgment response
            elif event["type"] == "send_ack":
                if game.winner and game.player_symbols.get(websocket) != game.winner:
                    game.ack = event["ack"]
                    await broadcast_state()

            elif event["type"] == "reset":
                game.board = [""] * 9
                game.turn = "X"
                game.winner = None
                game.task = None
                game.ack = None # Clear acknowledgment on reset
                await broadcast_state()

    except WebSocketDisconnect:
        if websocket in game.player_connections:
            game.player_connections.remove(websocket)
        game.player_symbols.pop(websocket, None)
        game.board = [""] * 9
        game.turn = "X"
        game.p1_choice = None
        game.winner = None
        game.task = None
        game.ack = None
        await broadcast_state()

if __name__ == "__main__":
    import uvicorn
    import os
    # Read port from environment variable or default to 80 for Render container
    port = int(os.environ.get("PORT", 80))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
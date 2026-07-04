from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import json

app = FastAPI()

# 1. MOUNT STATIC FILES (CSS, JS)
# This points FastAPI to look inside your "public" directory for your front-end code assets
if os.path.exists("public"):
    app.mount("/static", StaticFiles(directory="public"), name="public")

# 2. SERVE THE HTML FRONTEND ON THE ROOT ROUTE "/"
@app.get("/")
def get_index():
    index_path = os.path.join("public", "index.html")
    if os.path.exists(index_path):
        with open(index_path) as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content="<h1>Frontend files not found in /public folder</h1>", status_code=404)

def check_winner(board):
    wins = [
        [0,1,2], [3,4,5], [6,7,8],  # Rows
        [0,3,6], [1,4,7], [2,5,8],  # Columns
        [0,4,8], [2,4,6]            # Diagonals
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
        self.ack = None 

game = Game()

async def broadcast_state():
    # UPDATED: Create a structured dictionary instead of converting it manually to a string
    state_dict = {
        "board": game.board,
        "turn": game.turn,
        "players_count": len(game.player_connections),
        "winner": game.winner,
        "choices_set": game.p1_choice is not None,
        "task": game.task,
        "ack": game.ack 
    }
    for player in game.player_connections:
        try:
            # UPDATED: Use send_json so FastAPI formats and tags the headers properly over WebSockets
            await player.send_json(state_dict)
        except Exception:
            # Prevent crashes if a connection goes stale mid-transmission
            pass

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
            
            # Action: Player 1 selects X or O
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

            # Action: A player clicks a grid cell
            elif event["type"] == "move":
                user_symbol = game.player_symbols.get(websocket)
                if game.winner is None and game.board[event["index"]] == "" and user_symbol == game.turn:
                    game.board[event["index"]] = game.turn
                    game.winner = check_winner(game.board)
                    if not game.winner:
                        game.turn = "O" if game.turn == "X" else "X"
                    await broadcast_state()
            
            # Action: Winner issues a punishment/dare
            elif event["type"] == "send_task":
                if game.winner and game.player_symbols.get(websocket) == game.winner:
                    game.task = event["task"]
                    await broadcast_state()

            # Action: Loser types their response back
            elif event["type"] == "send_ack":
                if game.winner and game.player_symbols.get(websocket) != game.winner:
                    game.ack = event["ack"]
                    await broadcast_state()

            # Action: Restart the lobby match
            elif event["type"] == "reset":
                game.board = [""] * 9
                game.turn = "X"
                game.winner = None
                game.task = None
                game.ack = None 
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
    # Local fallback runner: let's you test on http://127.0.0.1:8000/ before pushing to production
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
import socket
import threading
import sys
import json

HOST = '0.0.0.0'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9002

class Connect4Server:
    def __init__(self):
        self.rows = 6
        self.cols = 7
        self.board = [[' ' for _ in range(self.cols)] for _ in range(self.rows)]
        self.current_turn = "R" # R for Red, Y for Yellow
        self.players = [] # list of sockets
        self.lock = threading.Lock()
        self.game_over = False
        self.player_map = {} # socket -> symbol

    def start(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen(2)

        try:
            while len(self.players) < 2:
                conn, addr = server_sock.accept()
                
                with self.lock:
                    self.players.append(conn)
                    # Assign symbol
                    symbol = "R" if len(self.players) == 1 else "Y"
                    self.player_map[conn] = symbol
                
                conn.sendall(json.dumps({"type": "INIT", "symbol": symbol}).encode() + b"\n")
                
                threading.Thread(target=self.handle_player, args=(conn, symbol)).start()
                
            self.broadcast({"type": "START", "turn": self.current_turn})
            
        except Exception:
            pass

    def handle_player(self, conn, symbol):
        buffer = ""
        try:
            while not self.game_over:
                data = conn.recv(1024).decode()
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line)
                        self.process_move(symbol, msg)
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
        finally:
            with self.lock:
                if conn in self.players:
                    self.players.remove(conn)
                conn.close()
            
            if not self.game_over:
                self.game_over = True
                self.broadcast({"type": "ERROR", "message": f"Player {symbol} disconnected"})

    def process_move(self, symbol, msg):
        if msg.get("type") != "MOVE":
            return
            
        col = msg.get("column")
        if col is None:
            return

        with self.lock:
            if self.game_over:
                return
            if symbol != self.current_turn:
                return
            
            # Find the first empty row in this column
            row = -1
            for r in range(self.rows - 1, -1, -1):
                if self.board[r][col] == ' ':
                    row = r
                    break
            
            if row == -1:
                # Column is full
                return
            
            self.board[row][col] = symbol
            
            # Check winner
            winner = self.check_winner(row, col, symbol)
            
            # Switch turn
            self.current_turn = "Y" if self.current_turn == "R" else "R"
            
            if winner:
                self.game_over = True
                self.broadcast({
                    "type": "UPDATE", 
                    "board": self.board, 
                    "turn": self.current_turn,
                    "last_move": {"row": row, "col": col, "symbol": symbol}
                })
                self.broadcast({"type": "GAME_OVER", "winner": winner})
            elif self.is_board_full():
                self.game_over = True
                self.broadcast({
                    "type": "UPDATE", 
                    "board": self.board, 
                    "turn": self.current_turn,
                    "last_move": {"row": row, "col": col, "symbol": symbol}
                })
                self.broadcast({"type": "GAME_OVER", "winner": "DRAW"})
            else:
                self.broadcast({
                    "type": "UPDATE", 
                    "board": self.board, 
                    "turn": self.current_turn,
                    "last_move": {"row": row, "col": col, "symbol": symbol}
                })

    def broadcast(self, msg):
        data = json.dumps(msg).encode() + b"\n"
        for p in self.players:
            try:
                p.sendall(data)
            except:
                pass

    def check_winner(self, r, c, symbol):
        # Check directions: horizontal, vertical, diagonal /, diagonal \
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        
        for dr, dc in directions:
            count = 1
            # Check positive direction
            for i in range(1, 4):
                nr, nc = r + dr*i, c + dc*i
                if 0 <= nr < self.rows and 0 <= nc < self.cols and self.board[nr][nc] == symbol:
                    count += 1
                else:
                    break
            # Check negative direction
            for i in range(1, 4):
                nr, nc = r - dr*i, c - dc*i
                if 0 <= nr < self.rows and 0 <= nc < self.cols and self.board[nr][nc] == symbol:
                    count += 1
                else:
                    break
            
            if count >= 4:
                return symbol
        return None

    def is_board_full(self):
        for c in range(self.cols):
            if self.board[0][c] == ' ':
                return False
        return True

if __name__ == "__main__":
    server = Connect4Server()
    server.start()

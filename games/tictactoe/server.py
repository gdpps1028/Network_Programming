import socket
import threading
import sys
import json

HOST = '0.0.0.0'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9000

class TicTacToeServer:
    def __init__(self):
        self.board = [" "]*9
        self.current_turn = "X"
        self.players = [] # list of sockets
        self.lock = threading.Lock()
        self.game_over = False

    def start(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen(2)
        print(f"Game Server started on {PORT}")

        try:
            while len(self.players) < 2:
                conn, addr = server_sock.accept()
                print(f"Player connected: {addr}")
                self.players.append(conn)
                
                # Assign symbol
                symbol = "X" if len(self.players) == 1 else "O"
                conn.sendall(json.dumps({"type": "INIT", "symbol": symbol}).encode() + b"\n")
                
                threading.Thread(target=self.handle_player, args=(conn, symbol)).start()
                
            print("Game starting!")
            self.broadcast({"type": "START", "turn": self.current_turn})
            
        except Exception as e:
            print(f"Error: {e}")

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
                    msg = json.loads(line)
                    self.process_move(symbol, msg)
        except Exception as e:
            print(f"Error handling player {symbol}: {e}")
        finally:
            conn.close()
            if not self.game_over:
                self.game_over = True
                self.broadcast({"type": "ERROR", "message": "Player disconnected"})

    def process_move(self, symbol, msg):
        if msg["type"] == "MOVE":
            pos = msg["position"]
            with self.lock:
                if self.game_over:
                    return
                if symbol != self.current_turn:
                    return
                if self.board[pos] != " ":
                    return
                
                self.board[pos] = symbol
                self.current_turn = "O" if self.current_turn == "X" else "X"
                
                winner = self.check_winner()
                if winner:
                    self.game_over = True
                    self.broadcast({"type": "UPDATE", "board": self.board, "turn": self.current_turn})
                    self.broadcast({"type": "GAME_OVER", "winner": winner})
                elif " " not in self.board:
                    self.game_over = True
                    self.broadcast({"type": "UPDATE", "board": self.board, "turn": self.current_turn})
                    self.broadcast({"type": "GAME_OVER", "winner": "DRAW"})
                else:
                    self.broadcast({"type": "UPDATE", "board": self.board, "turn": self.current_turn})

    def broadcast(self, msg):
        data = json.dumps(msg).encode() + b"\n"
        for p in self.players:
            try:
                p.sendall(data)
            except Exception as e:
                print(f"Error broadcasting: {e}")

    def check_winner(self):
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for a,b,c in wins:
            if self.board[a] == self.board[b] == self.board[c] and self.board[a] != " ":
                return self.board[a]
        return None

if __name__ == "__main__":
    server = TicTacToeServer()
    server.start()

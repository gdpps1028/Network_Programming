import socket
import sys
import json
import threading
import time

if len(sys.argv) < 5:
    print("Usage: client.py <username> <room_id> <host> <port>")
    sys.exit(1)

USERNAME = sys.argv[1]
ROOM_ID = sys.argv[2]
HOST = sys.argv[3]
PORT = int(sys.argv[4])

class TicTacToeClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.symbol = None
        self.my_turn = False
        self.board = [" "]*9
        self.running = True

    def start(self):
        try:
            self.sock.connect((HOST, PORT))
            print(f"Connected to Game Server at {HOST}:{PORT}")
            
            # Start listener thread
            threading.Thread(target=self.listen).start()
            
            self.input_loop()
        except Exception as e:
            print(f"Connection error: {e}")

    def listen(self):
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(1024).decode()
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    try:
                        msg = json.loads(line)
                        self.handle_message(msg)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON: {e}")
            except Exception as e:
                print(f"Socket error: {e}")
                break
        print("Disconnected from server.")
        self.running = False

    def handle_message(self, msg):
        type = msg["type"]
        if type == "INIT":
            self.symbol = msg["symbol"]
            print(f"You are player {self.symbol}")
        elif type == "START":
            print("Game Started!")
            self.print_board()
            if msg["turn"] == self.symbol:
                print("Your turn!")
                self.my_turn = True
            else:
                print("Opponent's turn.")
                self.my_turn = False
        elif type == "UPDATE":
            self.board = msg["board"]
            self.print_board()
            if msg["turn"] == self.symbol:
                print("Your turn!")
                self.my_turn = True
            else:
                print("Opponent's turn.")
                self.my_turn = False
        elif type == "GAME_OVER":
            winner = msg["winner"]
            if winner == "DRAW":
                print("Game Over! It's a Draw!")
            elif winner == self.symbol:
                print("Game Over! You Win!")
            else:
                print("Game Over! You Lose!")
            self.running = False
            self.sock.close()
            sys.exit(0) # Exit process
        elif type == "ERROR":
            print(f"Error: {msg['message']}")
            self.running = False

    def input_loop(self):
        print("Enter position (0-8) when it's your turn.")
        while self.running:
            # Wait for turn
            while not self.my_turn and self.running:
                time.sleep(0.1)
                
            if not self.running: break

            try:
                line = input()
                if not self.running: break
                
                if not self.my_turn:
                    print("Not your turn.")
                    continue
                
                try:
                    pos = int(line)
                    if 0 <= pos <= 8 and self.board[pos] == " ":
                        self.sock.sendall(json.dumps({"type": "MOVE", "position": pos}).encode() + b"\n")
                        self.my_turn = False # Wait for update
                    else:
                        print("Invalid move.")
                except ValueError:
                    print("Invalid input.")
            except EOFError:
                break

    def print_board(self):
        b = self.board
        print(f"\n {b[0]} | {b[1]} | {b[2]} ")
        print("---+---+---")
        print(f" {b[3]} | {b[4]} | {b[5]} ")
        print("---+---+---")
        print(f" {b[6]} | {b[7]} | {b[8]} \n")

if __name__ == "__main__":
    client = TicTacToeClient()
    client.start()

import socket
import sys
import json
import threading
import tkinter as tk
from tkinter import messagebox

if len(sys.argv) < 5:
    print("Usage: client.py <username> <room_id> <host> <port>")
    sys.exit(1)

USERNAME = sys.argv[1]
ROOM_ID = sys.argv[2]
HOST = sys.argv[3]
PORT = int(sys.argv[4])

class Connect4Client:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.symbol = None
        self.my_turn = False
        self.board = [[' ' for _ in range(7)] for _ in range(6)]
        self.running = True
        
        # UI Setup
        self.root = tk.Tk()
        self.root.title(f"Connect 4 - {USERNAME}")
        self.cell_size = 80
        self.width = 7 * self.cell_size
        self.height = 6 * self.cell_size + 50 # +50 for status bar
        
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height - 50, bg='blue')
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind("<Button-1>", self.on_click)
        
        self.status_label = tk.Label(self.root, text="Connecting...", font=("Arial", 16))
        self.status_label.pack(fill='x', pady=10)
        
        self.circles = [['' for _ in range(7)] for _ in range(6)]
        self.draw_board_grid()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def draw_board_grid(self):
        for r in range(6):
            for c in range(7):
                x0 = c * self.cell_size
                y0 = r * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size
                # Draw empty circles
                self.circles[r][c] = self.canvas.create_oval(x0 + 5, y0 + 5, x1 - 5, y1 - 5, fill='white', outline='white')

    def update_board_ui(self):
        for r in range(6):
            for c in range(7):
                color = 'white'
                if self.board[r][c] == 'R':
                    color = 'red'
                elif self.board[r][c] == 'Y':
                    color = 'yellow'
                self.canvas.itemconfig(self.circles[r][c], fill=color)

    def start(self):
        try:
            self.sock.connect((HOST, PORT))
            print(f"Connected to Game Server at {HOST}:{PORT}")
            
            # Start listener thread
            threading.Thread(target=self.listen, daemon=True).start()
            
            self.root.mainloop()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server: {e}")
            self.root.destroy()

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
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line)
                        self.root.after(0, self.handle_message, msg)
                    except Exception as e:
                        print(f"Error parsing json: {e}")
            except Exception as e:
                print(f"Socket error: {e}")
                break
        
        if self.running:
            self.running = False
            self.root.after(0, lambda: messagebox.showerror("Disconnected", "Disconnected from server."))
            self.root.after(0, self.root.destroy)

    def handle_message(self, msg):
        msg_type = msg.get("type")
        
        if msg_type == "INIT":
            self.symbol = msg["symbol"]
            color = "Red" if self.symbol == "R" else "Yellow"
            self.root.title(f"Connect 4 - {USERNAME} ({color})")
            self.status_label.config(text=f"You are {color}. Waiting for opponent...")
            
        elif msg_type == "START":
            turn = msg["turn"]
            self.update_turn_status(turn)
            
        elif msg_type == "UPDATE":
            self.board = msg["board"]
            self.update_board_ui()
            turn = msg["turn"]
            self.update_turn_status(turn)
            
        elif msg_type == "GAME_OVER":
            winner = msg["winner"]
            if winner == "DRAW":
                self.status_label.config(text="Game Over! It's a Draw!", fg="black")
                messagebox.showinfo("Game Over", "It's a Draw!")
            elif winner == self.symbol:
                self.status_label.config(text="Game Over! You WIN!", fg="green")
                messagebox.showinfo("Game Over", "You Win!")
            else:
                self.status_label.config(text="Game Over! You lose.", fg="red")
                messagebox.showinfo("Game Over", "You Lose.")
            
            self.running = False
            self.sock.close()

        elif msg_type == "ERROR":
            print(f"Error: {msg.get('message')}")

    def update_turn_status(self, turn):
        if turn == self.symbol:
            self.my_turn = True
            self.status_label.config(text="Your Turn!", fg="blue")
        else:
            self.my_turn = False
            self.status_label.config(text="Opponent's Turn", fg="black")

    def on_click(self, event):
        if not self.my_turn:
            return
            
        col = int(event.x / self.cell_size)
        if 0 <= col < 7:
            # Check if column is valid (not full)
            if self.board[0][col] != ' ':
                return # Column full
                
            msg = {"type": "MOVE", "column": col}
            try:
                self.sock.sendall(json.dumps(msg).encode() + b"\n")
                self.my_turn = False # Prevent multiple clicks
                self.status_label.config(text="Sending move...")
            except Exception as e:
                print(f"Error sending move: {e}")

    def on_close(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    client = Connect4Client()
    client.start()

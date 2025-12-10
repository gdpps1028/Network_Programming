import tkinter as tk
from tkinter import scrolledtext, messagebox
import select
import sys
from shared.protocol import *
from shared.utils import send_json, recv_json

class RoomGUI:
    def __init__(self, sock, room_id, username, is_host, game_id, launcher, plugin_manager, active_plugins, initial_players=None, initial_host=None, server_host=None):
        self.sock = sock
        self.room_id = room_id
        self.username = username
        self.is_host = is_host
        self.game_id = game_id
        self.launcher = launcher
        self.plugin_manager = plugin_manager
        self.active_plugins = active_plugins
        self.server_host = server_host
        self.players = initial_players if initial_players else [username]
        self.current_host = initial_host if initial_host else (username if is_host else self.players[0])
        
        self.root = tk.Tk()
        self.root.title(f"Room {room_id} - {username}")
        self.root.geometry("800x600")
        
        self.running = True
        self._create_widgets()
        self._setup_tags()
        
        # Start polling socket
        self._poll_job = None
        self._poll_loop()
        
    def _cleanup(self):
        self.running = False
        if self._poll_job:
            try:
                self.root.after_cancel(self._poll_job)
            except:
                pass
            self._poll_job = None
        try:
            self.root.destroy()
        except:
            pass

    def _setup_tags(self):
        # Color tags for different message types
        self.log_area.tag_configure("system", foreground="#2196F3")  # Blue
        self.log_area.tag_configure("join", foreground="#4CAF50")    # Green
        self.log_area.tag_configure("leave", foreground="#FF9800")   # Orange
        self.log_area.tag_configure("error", foreground="#f44336")   # Red
        self.log_area.tag_configure("chat", foreground="#333333")    # Dark gray
        
    def _create_widgets(self):
        # Top Info Bar
        info_frame = tk.Frame(self.root, pady=5)
        info_frame.pack(fill='x', padx=5)
        
        tk.Label(info_frame, text=f"Room ID: {self.room_id}", font=("Arial", 12, "bold")).pack(side='left')
        role = "Host" if self.is_host else "Guest"
        self.role_label = tk.Label(info_frame, text=f"Role: {role}", font=("Arial", 10))
        self.role_label.pack(side='right')
        
        # Main Content Frame (Chat + Player List)
        content_frame = tk.Frame(self.root)
        content_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Player List (right side) - pack first so it takes priority
        player_frame = tk.Frame(content_frame, width=150)
        player_frame.pack(side='right', fill='y', padx=(5, 0))
        player_frame.pack_propagate(False)
        
        tk.Label(player_frame, text="Players", font=("Arial", 10, "bold")).pack()
        self.player_listbox = tk.Listbox(player_frame, height=10, font=("Arial", 10))
        self.player_listbox.pack(fill='both', expand=True)
        self._update_player_list()
        
        # Chat/Log Area (left side)
        self.log_area = scrolledtext.ScrolledText(content_frame, state='disabled', height=15)
        self.log_area.pack(side='left', fill='both', expand=True)
        
        # Plugin UI Area (for emoji buttons, etc.)
        plugin_ui_frame = tk.Frame(self.root)
        plugin_ui_frame.pack(fill='x', padx=5)
        
        # Let plugins add their UI elements
        for p in self.active_plugins:
            if hasattr(p, "setup_gui"):
                p.setup_gui(plugin_ui_frame, None, None)  # msg_entry not created yet
        
        # Input Area
        input_frame = tk.Frame(self.root, pady=5)
        input_frame.pack(fill='x', padx=5)
        
        self.msg_entry = tk.Entry(input_frame)
        self.msg_entry.pack(side='left', fill='x', expand=True)
        self.msg_entry.bind("<Return>", self._send_chat)
        
        send_btn = tk.Button(input_frame, text="Send", command=self._send_chat)
        send_btn.pack(side='right', padx=5)
        
        # Give plugins access to the message entry now that it's created
        for p in self.active_plugins:
            if hasattr(p, "msg_entry"):
                p.msg_entry = self.msg_entry
        
        # Control Buttons
        btn_frame = tk.Frame(self.root, pady=10)
        btn_frame.pack(fill='x', padx=5)
        
        self.start_btn = tk.Button(btn_frame, text="Start Game", command=self._start_game, bg='#4CAF50', fg='white')
        if self.is_host:
            self.start_btn.pack(side='left', padx=5)
            
        leave_btn = tk.Button(btn_frame, text="Leave Room", command=self._leave_room, bg='#f44336', fg='white')
        leave_btn.pack(side='right', padx=5)
        
        self._append_log(f"Welcome to Room {self.room_id}!", "system")
        if self.is_host:
            self._append_log("You are the host. Click 'Start Game' when ready.", "system")
        else:
            self._append_log("Waiting for host to start the game...", "system")

    def _update_player_list(self):
        self.player_listbox.delete(0, tk.END)
        for i, player in enumerate(self.players):
            prefix = ""
            if player == self.current_host:
                prefix = "★ "  # Star for host
            display_name = f"{prefix}{player}"
            self.player_listbox.insert(tk.END, display_name)
            
            # Highlight current player with different text color
            if player == self.username:
                self.player_listbox.itemconfig(i, fg='#52eb34')  # Teal color

    def _append_log(self, text, tag=None):
        self.log_area.config(state='normal')
        if tag:
            self.log_area.insert(tk.END, text + "\n", tag)
        else:
            self.log_area.insert(tk.END, text + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def _send_chat(self, event=None):
        msg_text = self.msg_entry.get().strip()
        if not msg_text:
            return
            
        # Check plugins first (e.g. for commands)
        consumed = False
        for p in self.active_plugins:
            if hasattr(p, "handle_input") and p.handle_input(msg_text):
                consumed = True
                break
        
        if not consumed:
            # Send chat message to server
            msg = create_message(MSG_CHAT, {
                "room_id": self.room_id,
                "message": msg_text
            })
            send_json(self.sock, msg)
            
        self.msg_entry.delete(0, tk.END)

    def _start_game(self):
        if not self.is_host:
            return
            
        msg = create_message(MSG_START_GAME, {"room_id": self.room_id})
        send_json(self.sock, msg)
        self._append_log("Requesting game start...")

    def _leave_room(self):
        # Notify server
        msg = create_message(MSG_LEAVE_ROOM)
        send_json(self.sock, msg)
        
        # Consume response
        try:
            recv_json(self.sock)
        except Exception:
            pass
            
        self._cleanup()

    def _poll_socket(self):
        # Legacy entry point if called directly, redirect to loop
        self._poll_loop()

    def _poll_loop(self):
        if not self.running:
            return

        try:
            # Non-blocking check
            rlist, _, _ = select.select([self.sock], [], [], 0)
            if rlist:
                msg = recv_json(self.sock)
                if not msg:
                    self._append_log("Disconnected from server.")
                    messagebox.showerror("Error", "Disconnected from server.")
                    self._cleanup()
                    return
                
                self._handle_server_message(msg)
                
        except Exception as e:
            print(f"Socket error: {e}")
            self._cleanup()
            return
            
        if self.running:
            self._poll_job = self.root.after(100, self._poll_loop)

    def _handle_server_message(self, msg):
        msg_type = msg.get("type")
        
        if msg_type == MSG_GAME_STARTED:
            self._append_log("Game Starting!")
            port = msg["data"]["port"]
            # Use the server host from config.json, not from the message
            host = self.server_host if self.server_host else msg["data"]["host"]
            
            # Minimize window
            self.root.withdraw()
            
            # Launch game (blocking)
            # We need to do this slightly later to allow UI to update
            self.root.after(100, lambda: self._launch_and_restore(host, port))
            
        elif msg_type == MSG_PLUGIN_MESSAGE:
            payload = msg["data"]["payload"]
            sender = msg["data"]["sender"]
            
            # Pass to plugins
            for p in self.active_plugins:
                if hasattr(p, "handle_message"):
                    p.handle_message(payload, sender)
            
        elif msg_type == MSG_CHAT:
            sender = msg["data"]["sender"]
            message = msg["data"]["message"]
            self._append_log(f"{sender}: {message}")

        elif msg_type == MSG_ROOM_UPDATE:
            status = msg["data"]["status"]
            
            if status == "CLOSED":
                messagebox.showinfo("Room Closed", "The host has left the room. The room is now closed.")
                self._cleanup()
                return

            new_host = msg["data"]["host"]
            new_players = msg["data"]["players"]
            
            # Detect joins and leaves
            joined = msg["data"].get("joined")
            if joined:
                self._append_log(f"{joined} joined the room!", "join")
            
            old_players = set(self.players)
            new_players_set = set(new_players)
            
            # Detect leaves (not covered by joined field)
            for player in old_players - new_players_set:
                if player != joined:  # Don't double report
                    self._append_log(f"{player} left the room.", "leave")
            
            # Update player list and host
            self.players = new_players
            self.current_host = new_host
            self._update_player_list()
            
            # Update Host Status
            was_host = self.is_host
            self.is_host = (self.username == new_host)
            
            role = "Host" if self.is_host else "Guest"
            self.role_label.config(text=f"Role: {role}")
            
            if self.is_host and not was_host:
                self._append_log("🎉 You are now the Host!", "system")
                self.start_btn.pack(side='left', padx=5)
            elif not self.is_host and was_host:
                self.start_btn.pack_forget()
                
        elif msg.get("status") == STATUS_OK and msg.get("message") == "Game start requested":
            self._append_log("Server accepted start request.")
            
        elif msg.get("status") == STATUS_ERROR:
            self._append_log(f"Error: {msg.get('message')}")

    def _launch_and_restore(self, host, port):
        try:
            self.launcher.launch_game(self.game_id, self.room_id, host, port, self.is_host)
        except Exception as e:
            messagebox.showerror("Game Error", f"Failed to launch game: {e}")
        finally:
            # Restore window when game ends
            self.root.deiconify()
            self._append_log("Game finished.")

    def show(self):
        self.root.mainloop()

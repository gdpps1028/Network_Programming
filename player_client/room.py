import time
from shared.protocol import *
from shared.utils import send_json, recv_json
from player_client.game_launcher import GameLauncher
from player_client.plugin_manager import PluginManager
from player_client.gui_room import RoomGUI
from player_client.store import Store

class RoomContext:
    def __init__(self, sock, room_id, username):
        self.sock = sock
        self.room_id = room_id
        self.username = username

    def send_plugin_message(self, plugin_id, payload):
        msg = create_message(MSG_PLUGIN_MESSAGE, {
            "room_id": self.room_id,
            "plugin_id": plugin_id,
            "payload": payload
        })
        send_json(self.sock, msg)

class RoomManager:
    def __init__(self, sock, username):
        self.sock = sock
        self.username = username
        self.launcher = GameLauncher(username)
        self.plugin_manager = PluginManager(sock, username)
        self.store = Store(sock, username)
        self.active_plugins = []

    def create_room(self):
        # First select a game
        msg = create_message(MSG_LIST_GAMES)
        send_json(self.sock, msg)
        response = recv_json(self.sock)
        
        if not response or response["status"] != STATUS_OK:
            print("Failed to fetch games.")
            return

        games = response["data"]["games"]
        if not games:
            print("No games available.")
            return

        print("\nSelect game to host:")
        for i, game in enumerate(games):
            print(f"{i+1}. {game['name']}")
            
        try:
            idx = int(input("Choice: ")) - 1
            if not (0 <= idx < len(games)):
                print("Invalid choice.")
                return
            game = games[idx]
        except ValueError:
            print("Invalid input.")
            return

        msg = create_message(MSG_CREATE_ROOM, {"game_id": game["game_id"]})
        send_json(self.sock, msg)
        
        response = recv_json(self.sock)
        if response and response["status"] == STATUS_OK:
            room_id = response["data"]["room_id"]
            print(f"Room created! ID: {room_id}")
            
            # Auto-download game
            self.store.download_game_if_needed(game["game_id"])
            
            self.wait_in_room(room_id, game["game_id"], is_host=True, initial_players=[self.username], initial_host=self.username)
        else:
            print(f"Failed to create room: {response.get('message')}")

    def join_room(self):
        msg = create_message(MSG_LIST_ROOMS)
        send_json(self.sock, msg)
        response = recv_json(self.sock)
        
        if not response or response["status"] != STATUS_OK:
            print("Failed to fetch rooms.")
            return

        data = response.get("data")
        if not data:
            print("Server returned success but no data payload.")
            return

        rooms = data.get("rooms")
        if not rooms:
            print("No active rooms.")
            return

        print("\nActive Rooms:")
        print(f"{'ID':<5} | {'Game':<20} | {'Host':<15} | {'Status'}")
        print("-" * 60)
        for room in rooms:
            print(f"{room['id']:<5} | {room['game_name']:<20} | {room['host']:<15} | {room['status']}")

        room_id = input("Enter Room ID to join: ")
        
        msg = create_message(MSG_JOIN_ROOM, {"room_id": room_id})
        send_json(self.sock, msg)
        
        response = recv_json(self.sock)
        if response and response["status"] == STATUS_OK:
            room = response["data"]["room"]
            print(f"Joined room {room_id}!")
            
            # Auto-download game
            self.store.download_game_if_needed(room["game_id"])
            
            self.wait_in_room(room_id, room["game_id"], is_host=False, initial_players=room["players"], initial_host=room["host"])
        else:
            print(f"Failed to join room: {response.get('message')}")

    def wait_in_room(self, room_id, game_id, is_host, initial_players=None, initial_host=None):
        print("\nWaiting for game to start...")
        
        # Load Plugins
        context = RoomContext(self.sock, room_id, self.username)
        self.active_plugins = self.plugin_manager.load_plugins(context)
        for p in self.active_plugins:
            if hasattr(p, "on_room_join"):
                p.on_room_join(room_id)

        if is_host:
            print("Press 's' to start game when ready.")
        
        # Launch GUI
        print("Opening Room GUI...")
        try:
            gui = RoomGUI(
                self.sock, 
                room_id, 
                self.username, 
                is_host, 
                game_id, 
                self.launcher, 
                self.plugin_manager, 
                self.active_plugins,
                initial_players,
                initial_host
            )
            gui.show()
        except Exception as e:
            print(f"Error opening Room GUI: {e}")
            pass
            
        print("Left room.")

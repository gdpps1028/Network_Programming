import os
import subprocess
import sys
import json

class GameLauncher:
    def __init__(self, username):
        self.username = username
        self.downloads_dir = os.path.join("player_client", "downloads", username)

    def launch_game(self, game_id, room_id, server_host, server_port, is_host):
        game_dir = os.path.join(self.downloads_dir, game_id)
        if not os.path.exists(game_dir):
            print(f"Game {game_id} not found locally.")
            return False

        # Look for client.py entry point
        entry_point = os.path.join(game_dir, "client.py")
        if not os.path.exists(entry_point):
            # Try to find it in a subdirectory if the zip contained a folder
            subdirs = [d for d in os.listdir(game_dir) if os.path.isdir(os.path.join(game_dir, d))]
            if len(subdirs) == 1:
                entry_point = os.path.join(game_dir, subdirs[0], "client.py")
        
        if not os.path.exists(entry_point):
            print("Could not find game entry point (client.py).")
            return False

        print(f"Launching game {game_id} for room {room_id}...")
        
        # Launch game client with: username, room_id, server_host, server_port
        cmd = [sys.executable, "-u", entry_point, self.username, room_id, server_host, str(server_port)]
        
        try:
            # Launch the game subprocess
            subprocess.run(cmd)
            return True
        except Exception as e:
            print(f"Failed to launch game: {e}")
            return False

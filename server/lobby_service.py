import threading
import subprocess
import sys
import os
import socket
import time
import shutil
from shared.protocol import *

class LobbyService:
    def __init__(self, db, broadcast_func):
        self.db = db
        self.broadcast_func = broadcast_func
        self.rooms = {} # room_id -> room_info
        self.room_counter = 1
        self.lock = threading.Lock()
        self.next_port = 9000 # Start allocating game ports from 9000

    def handle_message(self, sock, msg_type, data, user_info):
        if msg_type == MSG_CREATE_ROOM:
            return self.handle_create_room(data, user_info)
        elif msg_type == MSG_JOIN_ROOM:
            return self.handle_join_room(data, user_info)
        elif msg_type == MSG_LIST_ROOMS:
            return self.handle_list_rooms()
        elif msg_type == MSG_START_GAME:
            return self.handle_start_game(data, user_info)
        elif msg_type == MSG_PLUGIN_MESSAGE:
            return self.handle_plugin_message(data, user_info)
        elif msg_type == MSG_LEAVE_ROOM:
            return self.handle_leave_room(user_info)
        elif msg_type == MSG_CHAT:
            return self.handle_chat(data, user_info)
        return create_response(STATUS_ERROR, message="Unknown lobby command")

    def handle_create_room(self, data, user_info):
        game_id = data.get("game_id")
        game = self.db.get_game(game_id)
        if not game:
            return create_response(STATUS_ERROR, message="Game not found")

        with self.lock:
            room_id = str(self.room_counter)
            self.room_counter += 1
            
            self.rooms[room_id] = {
                "id": room_id,
                "game_id": game_id,
                "game_name": game["name"],
                "host": user_info["username"],
                "players": [user_info["username"]],
                "max_players": game.get("max_players", 2), # Configurable per game, default 2
                "status": "WAITING"
            }
            
        return create_response(STATUS_OK, message="Room created", data={"room_id": room_id})

    def handle_join_room(self, data, user_info):
        room_id = data.get("room_id")
        
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return create_response(STATUS_ERROR, message="Room not found")
                
            if room["status"] != "WAITING":
                return create_response(STATUS_ERROR, message="Room is not waiting for players")
                
            if len(room["players"]) >= room["max_players"]:
                return create_response(STATUS_ERROR, message="Room is full")
                
            if user_info["username"] in room["players"]:
                return create_response(STATUS_ERROR, message="Already in room")
                
            room["players"].append(user_info["username"])
            
            # Broadcast update to other players
            msg = create_message(MSG_ROOM_UPDATE, {
                "room_id": room_id,
                "players": room["players"],
                "host": room["host"],
                "status": room["status"],
                "joined": user_info["username"]
            })
            existing_players = [p for p in room["players"] if p != user_info["username"]]
            self.broadcast_func(existing_players, msg)
            
        return create_response(STATUS_OK, message="Joined room", data={"room": room})

    def handle_list_rooms(self):
        with self.lock:
            rooms_list = []
            for r in self.rooms.values():
                room_data = r.copy()
                if "process" in room_data:
                    del room_data["process"]
                rooms_list.append(room_data)
            return create_response(STATUS_OK, data={"rooms": rooms_list})

    def handle_start_game(self, data, user_info):
        room_id = data.get("room_id")
        
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return create_response(STATUS_ERROR, message="Room not found")
                
            if room["host"] != user_info["username"]:
                return create_response(STATUS_ERROR, message="Only host can start game")
                
            # Check min players
            game_id = room["game_id"]
            game = self.db.get_game(game_id)
            min_players = game.get("min_players", 2)
            
            if len(room["players"]) < min_players:
                return create_response(STATUS_ERROR, message=f"Not enough players (min {min_players})")
            
            version = game["latest_version"]
            
            run_dir = os.path.join("server", "running_games", f"{game_id}_{version}")
            if not os.path.exists(run_dir):
                # Unzip if not exists
                import zipfile
                zip_path = os.path.join("server", "storage", "games", game_id, f"{version}.zip")
                if not os.path.exists(zip_path):
                     return create_response(STATUS_ERROR, message="Game files missing")
                
                os.makedirs(run_dir)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(run_dir)
                except zipfile.BadZipFile:
                    return create_response(STATUS_ERROR, message="Game files corrupted")
                except Exception as e:
                    return create_response(STATUS_ERROR, message=f"Failed to extract game files: {e}")
            
            # Find server entry point
            server_script = os.path.join(run_dir, "server.py")
            if not os.path.exists(server_script):
                subdirs = [d for d in os.listdir(run_dir) if os.path.isdir(os.path.join(run_dir, d)) and d != "__pycache__"]
                if len(subdirs) == 1:
                    server_script = os.path.join(run_dir, subdirs[0], "server.py")
            
            if not os.path.exists(server_script):
                return create_response(STATUS_ERROR, message="Game server script not found")
                
            port = self.next_port
            
            server_script_abs = os.path.abspath(server_script)
            server_dir_abs = os.path.dirname(server_script_abs)
            
            try:
                # python3 -u server.py <port>
                proc = subprocess.Popen(
                    [sys.executable, "-u", server_script_abs, str(port)], 
                    cwd=server_dir_abs,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                import re
                port = self.next_port 
                start_time = time.time()
                
                while time.time() - start_time < 5:
                    line = proc.stdout.readline()
                    if not line:
                        if proc.poll() is not None:
                            _, err = proc.communicate()
                            return create_response(STATUS_ERROR, message=f"Game process died: {err}")
                        break
                        
                    print(f"[{game_id}] {line.strip()}") 
                    
                    match = re.search(r"Game Server started on (\d+)", line)
                    if match:
                        port = int(match.group(1))
                        break

                def reader_thread(p):
                    try:
                        while p.poll() is None:
                            line = p.stdout.readline()
                            if line: print(f"[GAME LOG] {line.strip()}")
                    except: pass
                
                threading.Thread(target=reader_thread, args=(proc,), daemon=True).start()

                self.next_port = port + 1 
                
                room["process"] = proc
                room["port"] = port
                room["run_dir"] = run_dir
                room["status"] = "PLAYING"
            except Exception as e:
                return create_response(STATUS_ERROR, message=f"Failed to launch game server: {e}")
            
            # Broadcast GAME_STARTED to all players
            msg = create_message(MSG_GAME_STARTED, {
                "room_id": room_id,
                "port": port,
                "host": "127.0.0.1"
            })
            self.broadcast_func(room["players"], msg)
            
        return create_response(STATUS_OK, message="Game start requested")

    def handle_leave_room(self, user_info):
        self._remove_player_from_rooms(user_info["username"])
        return create_response(STATUS_OK, message="Left room")

    def handle_chat(self, data, user_info):
        room_id = data.get("room_id")
        message = data.get("message")
        
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return create_response(STATUS_ERROR, message="Room not found")
            
            if user_info["username"] not in room["players"]:
                return create_response(STATUS_ERROR, message="Not in room")
                
            msg = create_message(MSG_CHAT, {
                "room_id": room_id,
                "sender": user_info["username"],
                "message": message
            })
            self.broadcast_func(room["players"], msg)
            
        return create_response(STATUS_OK)

    def handle_player_disconnect(self, username):
        self._remove_player_from_rooms(username)

    def _remove_player_from_rooms(self, username):
        with self.lock:
            # Remove player from any rooms they are in
            for room_id, room in list(self.rooms.items()):
                if username in room["players"]:
                    is_host = (username == room["host"])
                    room["players"].remove(username)
                    
                    # If game was playing, stop it
                    if room.get("status") == "PLAYING":
                        print(f"Player {username} left/disconnected during game in room {room_id}. Stopping game server.")
                        if "process" in room:
                            try:
                                room["process"].terminate()
                                room["process"].wait()
                            except Exception as e:
                                print(f"Error killing game server: {e}")
                            del room["process"]
                        
                        # Cleanup running game directory
                        if "run_dir" in room:
                            try:
                                shutil.rmtree(room["run_dir"])
                                print(f"Cleaned up running game directory: {room['run_dir']}")
                            except Exception as e:
                                print(f"Error cleaning up running game directory: {e}")
                        
                        room["status"] = "WAITING"
                    
                    if is_host:
                        # Host left -> Close Room
                        print(f"Host {username} left room {room_id}. Closing room.")
                        
                        # Notify remaining players
                        if room["players"]:
                            msg = create_message(MSG_ROOM_UPDATE, {
                                "room_id": room_id,
                                "players": [],
                                "host": None,
                                "status": "CLOSED"
                            })
                            self.broadcast_func(room["players"], msg)
                        
                        del self.rooms[room_id]
                    
                    elif not room["players"]:
                        # Last player left -> Close Room
                        del self.rooms[room_id]
                    else:
                        # Guest left -> Update remaining players
                        msg = create_message(MSG_ROOM_UPDATE, {
                            "room_id": room_id,
                            "players": room["players"],
                            "host": room["host"],
                            "status": room["status"]
                        })
                        self.broadcast_func(room["players"], msg)

    def handle_plugin_message(self, data, user_info):
        room_id = data.get("room_id")
        plugin_id = data.get("plugin_id")
        payload = data.get("payload")
        
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return create_response(STATUS_ERROR, message="Room not found")
            
            if user_info["username"] not in room["players"]:
                return create_response(STATUS_ERROR, message="Not in room")
                
            # Broadcast to all players in room
            msg = create_message(MSG_PLUGIN_MESSAGE, {
                "room_id": room_id,
                "plugin_id": plugin_id,
                "sender": user_info["username"],
                "payload": payload
            })
            self.broadcast_func(room["players"], msg)
            
        return create_response(STATUS_OK)

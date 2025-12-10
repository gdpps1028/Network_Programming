import os
import shutil
from shared.protocol import *
from shared.utils import recv_file, send_json

class DeveloperService:
    def __init__(self, db):
        self.db = db
        self.storage_dir = os.path.join("server", "storage", "games")
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def handle_message(self, sock, msg_type, data, user_info):
        if msg_type == MSG_UPLOAD_GAME:
            return self.handle_upload_game(sock, data, user_info)
        elif msg_type == MSG_UPDATE_GAME:
            return self.handle_update_game(sock, data, user_info)
        elif msg_type == MSG_REMOVE_GAME:
            return self.handle_remove_game(data, user_info)
        elif msg_type == MSG_LIST_GAMES:
            return self.handle_list_my_games(user_info)
        return create_response(STATUS_ERROR, message="Unknown developer command")

    def handle_upload_game(self, sock, data, user_info):
        game_name = data.get("game_name")
        description = data.get("description")
        game_type = data.get("game_type")
        version = data.get("version")
        min_players = data.get("min_players")
        max_players = data.get("max_players")

        if min_players is None or max_players is None:
            return create_response(STATUS_ERROR, message="Missing min_players or max_players")
        
        try:
            min_players = int(min_players)
            max_players = int(max_players)
            if min_players < 1:
                return create_response(STATUS_ERROR, message="min_players must be at least 1")
            if min_players > max_players:
                return create_response(STATUS_ERROR, message="min_players cannot be greater than max_players")
        except ValueError:
            return create_response(STATUS_ERROR, message="Invalid player counts")
        
        # Generate a unique game ID (or use name if unique)
        game_id = f"{user_info['username']}_{game_name}"
        
        if self.db.get_game(game_id):
            return create_response(STATUS_ERROR, message="Game already exists")

        # Prepare to receive file
        game_dir = os.path.join(self.storage_dir, game_id)
        if not os.path.exists(game_dir):
            os.makedirs(game_dir)
            
        file_path = os.path.join(game_dir, f"{version}.zip")
        
        # Tell client we are ready to receive file
        send_json(sock, create_response(STATUS_OK, message="Ready to upload"))
        
        # Receive file
        if recv_file(sock, file_path):
            metadata = {
                "game_id": game_id,
                "name": game_name,
                "description": description,
                "type": game_type,
                "author": user_info["username"],
                "latest_version": version,
                "versions": [version],
                "min_players": min_players,
                "max_players": max_players
            }
            self.db.add_game(game_id, metadata)
            return create_response(STATUS_OK, message="Game uploaded successfully")
        else:
            return create_response(STATUS_ERROR, message="File upload failed")

    def handle_update_game(self, sock, data, user_info):
        game_id = data.get("game_id")
        version = data.get("version")
        min_players = data.get("min_players")
        max_players = data.get("max_players")
        
        # Optional validation if they provide it during update
        if min_players is not None and max_players is not None:
            try:
                min_players = int(min_players)
                max_players = int(max_players)
                if min_players < 1:
                    return create_response(STATUS_ERROR, message="min_players must be at least 1")
                if min_players > max_players:
                    return create_response(STATUS_ERROR, message="min_players cannot be greater than max_players")
            except ValueError:
                return create_response(STATUS_ERROR, message="Invalid player counts")
        
        game = self.db.get_game(game_id)
        if not game:
            return create_response(STATUS_ERROR, message="Game not found")
        
        if game["author"] != user_info["username"]:
            return create_response(STATUS_ERROR, message="Permission denied")
            
        if version in game["versions"]:
            return create_response(STATUS_ERROR, message="Version already exists")

        # Prepare to receive file
        game_dir = os.path.join(self.storage_dir, game_id)
        file_path = os.path.join(game_dir, f"{version}.zip")
        
        send_json(sock, create_response(STATUS_OK, message="Ready to upload update"))
        
        if recv_file(sock, file_path):
            # Delete old version zip files to save disk space
            old_versions = game["versions"]
            for old_version in old_versions:
                old_zip_path = os.path.join(game_dir, f"{old_version}.zip")
                if os.path.exists(old_zip_path):
                    try:
                        os.remove(old_zip_path)
                        print(f"Deleted old version: {old_zip_path}")
                    except Exception as e:
                        print(f"Error deleting old version {old_version}: {e}")
            
            # Update metadata - only keep latest version in versions list
            game["versions"] = [version]
            game["latest_version"] = version
            if min_players is not None: game["min_players"] = min_players
            if max_players is not None: game["max_players"] = max_players
            self.db.update_game(game_id, game)
            return create_response(STATUS_OK, message="Game updated successfully")
        else:
            return create_response(STATUS_ERROR, message="File upload failed")

    def handle_remove_game(self, data, user_info):
        game_id = data.get("game_id")
        game = self.db.get_game(game_id)
        
        if not game:
            return create_response(STATUS_ERROR, message="Game not found")
            
        if game["author"] != user_info["username"]:
            return create_response(STATUS_ERROR, message="Permission denied")
            
        self.db.remove_game(game_id)
        # Files are kept archived
        
        return create_response(STATUS_OK, message="Game removed successfully")

    def handle_list_my_games(self, user_info):
        all_games = self.db.get_all_games()
        my_games = [g for g in all_games.values() if g["author"] == user_info["username"]]
        return create_response(STATUS_OK, data={"games": my_games})

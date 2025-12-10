import os
from shared.protocol import *
from shared.utils import send_file, send_json

class StoreService:
    def __init__(self, db):
        self.db = db
        self.storage_dir = os.path.join("server", "storage", "games")

    def handle_message(self, sock, msg_type, data, user_info):
        if msg_type == MSG_LIST_GAMES:
            return self.handle_list_games()
        elif msg_type == MSG_GAME_DETAILS:
            return self.handle_game_details(data)
        elif msg_type == MSG_DOWNLOAD_GAME:
            return self.handle_download_game(sock, data)
        elif msg_type == MSG_SUBMIT_REVIEW:
            return self.handle_submit_review(data, user_info)
        elif msg_type == MSG_LIST_REVIEWS:
            return self.handle_list_reviews(data)
        elif msg_type == MSG_LIST_PLUGINS:
            return self.handle_list_plugins()
        elif msg_type == MSG_DOWNLOAD_PLUGIN:
            return self.handle_download_plugin(sock, data)
        return create_response(STATUS_ERROR, message="Unknown store command")

    def handle_list_games(self):
        games = list(self.db.get_all_games().values())
        return create_response(STATUS_OK, data={"games": games})

    def handle_game_details(self, data):
        game_id = data.get("game_id")
        game = self.db.get_game(game_id)
        if game:
            reviews = self.db.get_reviews(game_id)
            # Calculate average rating
            avg_rating = 0
            if reviews:
                avg_rating = sum(r["rating"] for r in reviews) / len(reviews)
            
            details = game.copy()
            details["reviews"] = reviews
            details["avg_rating"] = avg_rating
            return create_response(STATUS_OK, data={"game": details})
        return create_response(STATUS_ERROR, message="Game not found")

    def handle_download_game(self, sock, data):
        game_id = data.get("game_id")
        version = data.get("version") # Optional, defaults to latest
        
        game = self.db.get_game(game_id)
        if not game:
            return create_response(STATUS_ERROR, message="Game not found")
            
        if not version:
            version = game["latest_version"]
            
        file_path = os.path.join(self.storage_dir, game_id, f"{version}.zip")
        if not os.path.exists(file_path):
            return create_response(STATUS_ERROR, message="Version file not found")
            
        # Tell client we are ready to send
        send_json(sock, create_response(STATUS_OK, message="Starting download", data={"file_size": os.path.getsize(file_path)}))
        
        send_file(sock, file_path)
        
        # After sending file, we don't return a response here because the client expects the file stream
        # The client should read the file and then continue
        return None 

    def handle_submit_review(self, data, user_info):
        game_id = data.get("game_id")
        rating = data.get("rating")
        comment = data.get("comment")
        
        if not (1 <= rating <= 5):
            return create_response(STATUS_ERROR, message="Rating must be between 1 and 5")
            
        self.db.add_review(game_id, user_info["username"], rating, comment)
        return create_response(STATUS_OK, message="Review submitted")

    def handle_list_reviews(self, data):
        game_id = data.get("game_id")
        reviews = self.db.get_reviews(game_id)
        return create_response(STATUS_OK, data={"reviews": reviews})

    def handle_list_plugins(self):
        # List directories in server/storage/plugins
        plugins_dir = os.path.join("server", "storage", "plugins")
        if not os.path.exists(plugins_dir):
            return create_response(STATUS_OK, data={"plugins": []})
            
        plugins = []
        for name in os.listdir(plugins_dir):
            if os.path.isdir(os.path.join(plugins_dir, name)):
                plugins.append({"name": name, "description": "A plugin"})
        return create_response(STATUS_OK, data={"plugins": plugins})

    def handle_download_plugin(self, sock, data):
        plugin_name = data.get("plugin_name")
        plugin_path = os.path.join("server", "storage", "plugins", plugin_name)
        
        if not os.path.exists(plugin_path):
            return create_response(STATUS_ERROR, message="Plugin not found")
            
        # Zip it on the fly to a temp file
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        try:
            zip_path = os.path.join(temp_dir, f"{plugin_name}.zip")
            shutil.make_archive(os.path.join(temp_dir, plugin_name), 'zip', plugin_path)
            
            send_json(sock, create_response(STATUS_OK, message="Starting download", data={"file_size": os.path.getsize(zip_path)}))
            send_file(sock, zip_path)
        finally:
            shutil.rmtree(temp_dir)
        
        return None

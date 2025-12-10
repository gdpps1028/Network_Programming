import json
import os
import threading

class Database:
    def __init__(self, storage_dir="server/storage"):
        self.storage_dir = storage_dir
        self.users_file = os.path.join(storage_dir, "users.json")
        self.games_file = os.path.join(storage_dir, "games.json")
        self.reviews_file = os.path.join(storage_dir, "reviews.json")
        self.lock = threading.Lock()
        
        self._ensure_storage()
        self.users = self._load_data(self.users_file)
        self.games = self._load_data(self.games_file)
        self.reviews = self._load_data(self.reviews_file)

    def _ensure_storage(self):
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def _load_data(self, filepath):
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return {}

    def _save_data(self, filepath, data):
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    def register_user(self, username, password, role):
        with self.lock:
            # Check if this specific role:username exists
            user_key = f"{role}:{username}"
            if user_key in self.users:
                return False
            
            self.users[user_key] = {
                "username": username,
                "password": password,
                "role": role
            }
            self._save_data(self.users_file, self.users)
            return True

    def login_user(self, username, password, role):
        with self.lock:
            user_key = f"{role}:{username}"
            user = self.users.get(user_key)

            if user and user["password"] == password:
                return True
            return False

    def add_game(self, game_id, metadata):
        with self.lock:
            self.games[game_id] = metadata
            self._save_data(self.games_file, self.games)

    def update_game(self, game_id, metadata):
        with self.lock:
            if game_id in self.games:
                self.games[game_id].update(metadata)
                self._save_data(self.games_file, self.games)
                return True
            return False

    def remove_game(self, game_id):
        with self.lock:
            if game_id in self.games:
                del self.games[game_id]
                self._save_data(self.games_file, self.games)
                return True
            return False

    def get_all_games(self):
        with self.lock:
            return self.games

    def get_game(self, game_id):
        with self.lock:
            return self.games.get(game_id)

    def add_review(self, game_id, username, rating, comment):
        with self.lock:
            if game_id not in self.reviews:
                self.reviews[game_id] = []
            
            self.reviews[game_id].append({
                "username": username,
                "rating": rating,
                "comment": comment
            })
            self._save_data(self.reviews_file, self.reviews)

    def get_reviews(self, game_id):
        with self.lock:
            return self.reviews.get(game_id, [])

import os
import shutil
import zipfile
import tempfile
from shared.protocol import *
from shared.utils import send_json, recv_json, recv_file

class Store:
    def __init__(self, sock, username):
        self.sock = sock
        self.username = username
        self.downloads_dir = os.path.join("player_client", "downloads", username)
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)

    def browse_store(self):
        msg = create_message(MSG_LIST_GAMES)
        send_json(self.sock, msg)
        response = recv_json(self.sock)
        
        if not response or response["status"] != STATUS_OK:
            print(f"Failed to load games: {response.get('message') if response else 'No response'}")
            return

        games = response["data"]["games"]
        if not games:
            print("No games available in the store.")
            return

        while True:
            print("\n=== Game Store ===")
            print(f"{'No.':<4} | {'Name':<20} | {'Type':<10} | {'Version':<10}")
            print("-" * 50)
            for i, game in enumerate(games):
                print(f"{i+1:<4} | {game['name']:<20} | {game['type']:<10} | {game['latest_version']:<10}")
            print("0. Back")

            choice = input("Select game number to view details (0 to back): ")
            if choice == '0':
                return
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(games):
                    self.view_game_details(games[idx]["game_id"])
                else:
                    print("Invalid choice.")
            except ValueError:
                print("Invalid input.")

    def view_game_details(self, game_id):
        msg = create_message(MSG_GAME_DETAILS, {"game_id": game_id})
        send_json(self.sock, msg)
        response = recv_json(self.sock)
        
        if not response or response["status"] != STATUS_OK:
            print("Failed to get game details.")
            return

        game = response["data"]["game"]
        print(f"\n=== {game['name']} ===")
        print(f"Author: {game['author']}")
        print(f"Type: {game['type']}")
        print(f"Latest Version: {game['latest_version']}")
        print(f"Description: {game['description']}")
        print(f"Average Rating: {game.get('avg_rating', 0):.1f}")
        
        print("\n--- Reviews ---")
        reviews = game.get("reviews", [])
        if reviews:
            for r in reviews:
                print(f"{r['username']}: {r['rating']}/5 - {r['comment']}")
        else:
            print("No reviews yet.")

        print("\nOptions:")
        print("1. Download/Update Game")
        print("2. Write a Review")
        print("3. Back")
        
        choice = input("Select option: ")
        if choice == '1':
            self.download_game(game)
        elif choice == '2':
            self.write_review(game_id)

    def download_game(self, game):
        game_id = game["game_id"]
        version = game["latest_version"]
        
        # Check if already downloaded
        game_dir = os.path.join(self.downloads_dir, game_id)
        version_file = os.path.join(game_dir, "version.txt")
        current_version = None
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                current_version = f.read().strip()
        
        if current_version == version:
            print("You already have the latest version.")
            confirm = input("Force re-download? (y/n): ")
            if confirm.lower() != 'y':
                return

        print(f"Downloading {game['name']} version {version}...")
        msg = create_message(MSG_DOWNLOAD_GAME, {"game_id": game_id, "version": version})
        send_json(self.sock, msg)
        
        response = recv_json(self.sock)
        if response and response["status"] == STATUS_OK:
            # Receive file
            temp_zip = os.path.join(self.downloads_dir, f"{game_id}.zip")
            if recv_file(self.sock, temp_zip):
                print("Download complete. Installing...")
                
                # Unzip
                if os.path.exists(game_dir):
                    shutil.rmtree(game_dir)
                os.makedirs(game_dir)
                
                try:
                    with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                        zip_ref.extractall(game_dir)
                    
                    # Write version file
                    with open(version_file, 'w') as f:
                        f.write(version)
                        
                    os.remove(temp_zip)
                    print("Installation successful!")
                except zipfile.BadZipFile:
                    print("Error: Downloaded file is corrupted.")
            else:
                print("Download failed during file transfer.")
        else:
            print(f"Download failed: {response.get('message')}")

    def write_review(self, game_id):
        print("\n--- Write Review ---")
        try:
            rating = int(input("Rating (1-5): "))
            if not (1 <= rating <= 5):
                print("Rating must be between 1 and 5.")
                return
        except ValueError:
            print("Invalid input.")
            return
            
        comment = input("Comment: ")
        
        msg = create_message(MSG_SUBMIT_REVIEW, {
            "game_id": game_id,
            "rating": rating,
            "comment": comment
        })
        send_json(self.sock, msg)
        
        response = recv_json(self.sock)
        if response and response["status"] == STATUS_OK:
            print("Review submitted!")
        else:
            print(f"Failed to submit review: {response.get('message')}")

    def download_game_if_needed(self, game_id):
        # Fetch game details to get latest version
        msg = create_message(MSG_GAME_DETAILS, {"game_id": game_id})
        send_json(self.sock, msg)
        response = recv_json(self.sock)
        
        if not response or response["status"] != STATUS_OK:
            print(f"Failed to get game details for auto-download: {response.get('message') if response else 'No response'}")
            return False

        game = response["data"]["game"]
        version = game["latest_version"]
        
        # Check local version
        game_dir = os.path.join(self.downloads_dir, game_id)
        version_file = os.path.join(game_dir, "version.txt")
        current_version = None
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                current_version = f.read().strip()
        
        if current_version == version:
            # Already up to date
            return True

        print(f"Auto-downloading {game['name']} (v{version})...")
        
        # Reuse download logic but without prompts
        # We can call download_game but it has prompts.
        # Let's duplicate the core download logic or refactor.
        # Refactoring is better but for now let's just implement the core logic here to avoid breaking existing flow.
        
        msg = create_message(MSG_DOWNLOAD_GAME, {"game_id": game_id, "version": version})
        send_json(self.sock, msg)
        
        response = recv_json(self.sock)
        if response and response["status"] == STATUS_OK:
            temp_zip = os.path.join(self.downloads_dir, f"{game_id}.zip")
            if recv_file(self.sock, temp_zip):
                print("Download complete. Installing...")
                if os.path.exists(game_dir):
                    shutil.rmtree(game_dir)
                os.makedirs(game_dir)
                
                try:
                    with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                        zip_ref.extractall(game_dir)
                    
                    with open(version_file, 'w') as f:
                        f.write(version)
                        
                    os.remove(temp_zip)
                    print("Installation successful!")
                    return True
                except zipfile.BadZipFile:
                    print("Error: Downloaded file is corrupted.")
                    return False
            else:
                print("Download failed during file transfer.")
                return False
        else:
            print(f"Download failed: {response.get('message')}")
            return False

import sys
import os
import shutil
import tempfile

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.protocol import *
from shared.utils import send_json, recv_json, send_file
from developer_client.game_manager import GameManager
from developer_client.gui_upload import GameUploadDialog

class Menu:
    def __init__(self, sock, username):
        self.sock = sock
        self.username = username
        self.game_manager = GameManager()

    def show_main_menu(self):
        while True:
            print("\n=== Developer Main Menu ===")
            print("1. Upload New Game")
            print("2. Update Existing Game")
            print("3. Remove Game")
            print("4. List My Games")
            print("5. Logout")
            
            choice = input("Select option (1-5): ")
            
            if choice == '1':
                self.upload_game()
            elif choice == '2':
                self.update_game()
            elif choice == '3':
                self.remove_game()
            elif choice == '4':
                self.list_games()
            elif choice == '5':
                # Send logout message to server before returning to auth menu
                try:
                    send_json(self.sock, create_message(MSG_LOGOUT))
                except:
                    pass
                print("Logged out successfully.")
                return
            else:
                print("Invalid option. Please try again.")

    def _process_game_packaging_and_upload(self, msg, path, version):
        temp_dir = tempfile.mkdtemp()
        try:
            zip_path = os.path.join(temp_dir, f"{version}.zip")
            
            print("Packaging game...")
            if not self.game_manager.package_game(path, zip_path):
                return

            send_json(self.sock, msg)
            
            # Wait for Ready signal or error
            response = recv_json(self.sock)
            if response and response["status"] == STATUS_OK:
                print("Uploading game files...")
                send_file(self.sock, zip_path)
                
                # Wait for final confirmation
                final_response = recv_json(self.sock)
                if final_response and final_response["status"] == STATUS_OK:
                    print("Operation successful!")
                else:
                    print(f"Operation failed: {final_response.get('message')}")
            else:
                print(f"Server rejected operation: {response.get('message')}")
        finally:
            shutil.rmtree(temp_dir)

    def upload_game(self):
        print("\n--- Upload New Game ---")
        print("Opening GUI upload dialog...")
        
        try:
            dialog = GameUploadDialog()
            result = dialog.show()
        except Exception as e:
            print(f"Error opening GUI: {e}")
            return

        if not result:
            print("Upload cancelled.")
            return

        msg = create_message(MSG_UPLOAD_GAME, {
            "game_name": result["name"],
            "description": result["description"],
            "game_type": result["game_type"],
            "version": result["version"],
            "min_players": result["min_players"],
            "max_players": result["max_players"]
        })
        
        self._process_game_packaging_and_upload(msg, result["path"], result["version"])

    def update_game(self):
        print("\n--- Update Game ---")
        games = self._fetch_my_games()
        if not games:
            print("No games found.")
            return

        print("Select game to update:")
        for i, game in enumerate(games):
            print(f"{i+1}. {game['name']} (Latest: {game['latest_version']})")
            
        try:
            idx = int(input("Choice: ")) - 1
            if not (0 <= idx < len(games)):
                print("Invalid choice.")
                return
            game = games[idx]
        except ValueError:
            print("Invalid input.")
            return

        print("Opening update dialog...")
        try:
            dialog = GameUploadDialog(current_version=game['latest_version'])
            # Pre-fill game info
            dialog.name_entry.insert(0, game['name'])
            dialog.name_entry.config(state='disabled')
            dialog.desc_entry.insert(0, game.get('description', ''))
            dialog.type_var.set(game.get('type', 'CLI'))
            dialog.min_players_spin.set(game.get('min_players', 2))
            dialog.max_players_spin.set(game.get('max_players', 2))
            
            result = dialog.show()
        except Exception as e:
            print(f"Error opening GUI: {e}")
            return
        
        if not result:
            print("Update cancelled.")
            return
        
        msg = create_message(MSG_UPDATE_GAME, {
            "game_id": game["game_id"],
            "version": result["version"],
            "min_players": result["min_players"],
            "max_players": result["max_players"]
        })

        self._process_game_packaging_and_upload(msg, result["path"], result["version"])

    def remove_game(self):
        print("\n--- Remove Game ---")
        games = self._fetch_my_games()
        if not games:
            print("No games found.")
            return

        print("Select game to remove:")
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

        confirm = input(f"Are you sure you want to remove {game['name']}? (y/n): ")
        if confirm.lower() != 'y':
            return

        msg = create_message(MSG_REMOVE_GAME, {"game_id": game["game_id"]})
        send_json(self.sock, msg)
        
        response = recv_json(self.sock)
        if response and response["status"] == STATUS_OK:
            print("Game removed successfully!")
        else:
            print(f"Removal failed: {response.get('message')}")

    def list_games(self):
        print("\n--- My Games ---")
        games = self._fetch_my_games()
        if not games:
            print("No games found.")
            return
            
        print(f"{'Name':<20} | {'Type':<10} | {'Version':<10} | {'Description'}")
        print("-" * 60)
        for game in games:
            print(f"{game['name']:<20} | {game['type']:<10} | {game['latest_version']:<10} | {game['description']}")

    def _fetch_my_games(self):
        msg = create_message(MSG_LIST_GAMES)
        send_json(self.sock, msg)
        response = recv_json(self.sock)
        if response and response["status"] == STATUS_OK:
            return response["data"]["games"]
        return []

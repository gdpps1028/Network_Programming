import sys
import os

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from player_client.store import Store
from player_client.room import RoomManager
from player_client.plugin_manager import PluginManager
from shared.protocol import MSG_LOGOUT, create_message
from shared.utils import send_json

class Menu:
    def __init__(self, sock, username, server_host):
        self.sock = sock
        self.username = username
        self.server_host = server_host
        self.store = Store(sock, username)
        self.room_manager = RoomManager(sock, username, server_host)
        self.plugin_manager = PluginManager(sock, username)

    def show_main_menu(self):
        while True:
            print("\n=== Player Main Menu ===")
            print("1. Browse Store / Download Games")
            print("2. Create Room")
            print("3. Join Room")
            print("4. Plugin Store")
            print("5. Logout")
            
            choice = input("Select option (1-5): ")
            
            if choice == '1':
                self.store.browse_store()
            elif choice == '2':
                self.room_manager.create_room()
            elif choice == '3':
                self.room_manager.join_room()
            elif choice == '4':
                self.plugin_manager.browse_plugins()
            elif choice == '5':
                # Send logout message to server before returning to auth menu
                try:
                    send_json(self.sock, create_message(MSG_LOGOUT))
                except:
                    pass
                print("Logged out successfully.")
                return
            else:
                print("Invalid option.")

import socket
import sys
import os

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from developer_client.auth import Auth
from developer_client.menu import Menu
from shared.protocol import MSG_LOGOUT, create_message
from shared.utils import send_json
from shared.config import ConfigManager

def main():
    # Load server configuration from config.json
    config_manager = ConfigManager()
    config = config_manager.get_server_config()
    
    if not config:
        print("\nError: No configuration file found!")
        print("Please create a 'config.json' file in the project root.")
        print("See 'config.json.example' for the required format.")
        return
    
    host, port = config
    
    print(f"\nConnecting to Game Server at {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print("Connected successfully!")
    except ConnectionRefusedError:
        print(f"Error: Could not connect to server at {host}:{port}")
        print("Please check:")
        print("1. Is the server running?")
        print("2. Is the address correct in config.json?")
        return
    except Exception as e:
        print(f"Connection error: {e}")
        return

    auth = Auth(sock)
    
    while True:
        print("\n=== Developer Client ===")
        print("1. Login")
        print("2. Register")
        print("3. Exit")
        
        choice = input("Select option: ")
        
        if choice == '1':
            if auth.login():
                menu = Menu(sock, auth.username)
                menu.show_main_menu()
                # After logout, loop back to auth menu
        elif choice == '2':
            auth.register()
        elif choice == '3':
            break
        else:
            print("Invalid option.")

    # Cleanup
    try:
        send_json(sock, create_message(MSG_LOGOUT))
    except:
        pass
    sock.close()
    print("Goodbye!")

if __name__ == "__main__":
    main()

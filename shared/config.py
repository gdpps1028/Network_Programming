import json
import os

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8888
CONFIG_FILE = 'config.json'

class ConfigManager:
    def __init__(self, config_path=None):
        if config_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, CONFIG_FILE)
        self.config_path = config_path
    
    def get_server_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    host = config.get('server', {}).get('host', DEFAULT_HOST)
                    port = config.get('server', {}).get('port', DEFAULT_PORT)
                    return (host, port)
        except Exception as e:
            print(f"Warning: Could not read config file: {e}")
        return None
    
    def save_server_config(self, host, port):
        try:
            config = {}
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r') as f:
                        config = json.load(f)
                except Exception:
                    pass
            
            # Update server config
            config['server'] = {
                'host': host,
                'port': port
            }
            
            # Write back to file
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            return True
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")
            return False

def get_server_address(args_host=None, args_port=None, prompt_on_missing=True):
    config_manager = ConfigManager()
    
    if args_host and args_port:
        return (args_host, args_port, False)
    
    config = config_manager.get_server_config()
    if config:
        host, port = config
        if args_host:
            host = args_host
        if args_port:
            port = args_port
        return (host, port, False)
    
    if prompt_on_missing:
        print("\nNo configuration found.")
        print("Please enter the server connection details:")
        
        while True:
            host_input = input(f"Server address [{DEFAULT_HOST}]: ").strip()
            host = host_input if host_input else DEFAULT_HOST
            
            port_input = input(f"Server port [{DEFAULT_PORT}]: ").strip()
            try:
                port = int(port_input) if port_input else DEFAULT_PORT
                break
            except ValueError:
                print("Invalid port number. Please try again.")
        
        save = input("Save this configuration? (y/n) [y]: ").strip().lower()
        should_save = save != 'n'
        
        return (host, port, should_save)
    
    return (DEFAULT_HOST, DEFAULT_PORT, False)

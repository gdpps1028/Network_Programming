import os
import shutil
import zipfile
import json
import importlib.util
import sys
from shared.protocol import *
from shared.utils import send_json, recv_json, recv_file

class PluginManager:
    def __init__(self, sock, username):
        self.sock = sock
        self.username = username
        # User-specific plugins directory
        self.plugins_dir = os.path.join("player_client", "plugins", username)
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
        self.loaded_plugins = []

    def browse_plugins(self):
        """Main plugin management menu."""
        while True:
            print("\n=== Plugin Manager ===")
            print("1. Download Plugins (Plugin Store)")
            print("2. View Installed Plugins")
            print("3. Remove Installed Plugin")
            print("0. Back")
            
            choice = input("Select option: ")
            
            if choice == '0':
                return
            elif choice == '1':
                self._browse_plugin_store()
            elif choice == '2':
                self._list_installed_plugins()
            elif choice == '3':
                self._remove_plugin()
            else:
                print("Invalid option.")
    
    def _browse_plugin_store(self):
        """Browse and download plugins from the server."""
        msg = create_message(MSG_LIST_PLUGINS)
        send_json(self.sock, msg)
        response = recv_json(self.sock)
        
        if not response or response["status"] != STATUS_OK:
            print("Failed to load plugins.")
            return

        plugins = response["data"]["plugins"]
        if not plugins:
            print("No plugins available in store.")
            return

        # Get list of installed plugins
        installed = self._get_installed_plugin_names()

        print("\n=== Plugin Store ===")
        for i, p in enumerate(plugins):
            status = " [INSTALLED]" if p['name'] in installed else ""
            print(f"{i+1}. {p['name']} - {p['description']}{status}")
            
        choice = input("Select plugin to download (0 to back): ")
        if choice == '0':
            return
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(plugins):
                plugin_name = plugins[idx]["name"]
                if plugin_name in installed:
                    confirm = input(f"{plugin_name} is already installed. Reinstall? (y/n): ")
                    if confirm.lower() != 'y':
                        return
                self.download_plugin(plugin_name)
        except ValueError:
            print("Invalid input.")
    
    def _get_installed_plugin_names(self):
        """Get list of installed plugin directory names."""
        if not os.path.exists(self.plugins_dir):
            return set()
        return {name for name in os.listdir(self.plugins_dir) 
                if os.path.isdir(os.path.join(self.plugins_dir, name))}
    
    def _list_installed_plugins(self):
        """Display all installed plugins."""
        installed = self._get_installed_plugin_names()
        
        if not installed:
            print("\nNo plugins installed.")
            return
            
        print("\n=== Installed Plugins ===")
        for i, name in enumerate(sorted(installed), 1):
            print(f"{i}. {name}")
        print(f"\nTotal: {len(installed)} plugin(s)")
        input("Press Enter to continue...")
    
    def _remove_plugin(self):
        """Remove an installed plugin."""
        installed = sorted(self._get_installed_plugin_names())
        
        if not installed:
            print("\nNo plugins installed.")
            return
            
        print("\n=== Remove Plugin ===")
        for i, name in enumerate(installed, 1):
            print(f"{i}. {name}")
        print("0. Cancel")
            
        choice = input("Select plugin to remove: ")
        if choice == '0':
            return
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(installed):
                plugin_name = installed[idx]
                confirm = input(f"Are you sure you want to remove '{plugin_name}'? (y/n): ")
                if confirm.lower() == 'y':
                    self._do_remove_plugin(plugin_name)
        except ValueError:
            print("Invalid input.")
    
    def _do_remove_plugin(self, plugin_name):
        """Actually remove the plugin directory."""
        plugin_path = os.path.join(self.plugins_dir, plugin_name)
        if os.path.exists(plugin_path):
            shutil.rmtree(plugin_path)
            print(f"Plugin '{plugin_name}' removed successfully!")
        else:
            print(f"Plugin '{plugin_name}' not found.")

    def download_plugin(self, plugin_name):
        print(f"Downloading {plugin_name}...")
        msg = create_message(MSG_DOWNLOAD_PLUGIN, {"plugin_name": plugin_name})
        send_json(self.sock, msg)
        
        response = recv_json(self.sock)
        if response and response["status"] == STATUS_OK:
            temp_zip = os.path.join(self.plugins_dir, f"{plugin_name}.zip")
            if recv_file(self.sock, temp_zip):
                # Unzip
                plugin_path = os.path.join(self.plugins_dir, plugin_name)
                if os.path.exists(plugin_path):
                    shutil.rmtree(plugin_path)
                os.makedirs(plugin_path)
                
                try:
                    with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                        zip_ref.extractall(plugin_path)
                    
                    os.remove(temp_zip)
                    print("Plugin installed!")
                except zipfile.BadZipFile:
                    print("Error: Downloaded plugin file is corrupted.")
                except Exception as e:
                    print(f"Error extracting plugin: {e}")
            else:
                print("Download failed (recv_file returned False).")
        else:
            print(f"Download failed: {response.get('message')}")

    def load_plugins(self, context):
        self.loaded_plugins = []
        if not os.path.exists(self.plugins_dir):
            return []
            
        for name in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, name)
            if os.path.isdir(plugin_path):
                # Look for main.py
                main_file = os.path.join(plugin_path, "main.py")
                if os.path.exists(main_file):
                    try:
                        spec = importlib.util.spec_from_file_location(f"plugins.{name}", main_file)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        if hasattr(module, "Plugin"):
                            plugin_instance = module.Plugin(context)
                            plugin_instance.on_load()
                            self.loaded_plugins.append(plugin_instance)
                    except Exception as e:
                        print(f"Failed to load plugin {name}: {e}")
        return self.loaded_plugins

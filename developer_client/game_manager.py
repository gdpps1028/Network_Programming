import os
import shutil

class GameManager:
    def validate_game(self, game_path):
        required_files = ["server.py", "client.py"]
        missing_files = []
        
        for req_file in required_files:
            file_path = os.path.join(game_path, req_file)
            if not os.path.exists(file_path):
                missing_files.append(req_file)
        
        return (len(missing_files) == 0, missing_files)

    def package_game(self, game_path, output_path):
        # Zips the game directory after validating
        if not os.path.exists(game_path):
            print(f"Error: Game path {game_path} does not exist.")
            return False
        
        # Validate that required files exist
        is_valid, missing_files = self.validate_game(game_path)
        if not is_valid:
            print(f"Error: Game is missing required files: {', '.join(missing_files)}")
            print("A valid game must contain both server.py and client.py")
            return False
            
        try:
            # Create a zip file
            base_name = os.path.splitext(output_path)[0]
            shutil.make_archive(base_name, 'zip', game_path)
            return True
        except Exception as e:
            print(f"Error packaging game: {e}")
            return False

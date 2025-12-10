import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os

class GameUploadDialog:
    def __init__(self, current_version=None):
        """
        current_version: If provided (e.g. "1.2.3"), the new version must be greater.
        """
        self.result = None
        self.current_version = current_version
        self.root = tk.Tk()
        self.root.title("Upload New Game" if not current_version else "Update Game")
        self.root.geometry("600x500")
        
        self._create_widgets()
        
    def _create_widgets(self):
        # Configure grid for resizing
        self.root.grid_columnconfigure(1, weight=1)
        
        # Padding
        pad_opts = {'padx': 10, 'pady': 5}
        
        row_idx = 0

        # Game Name
        tk.Label(self.root, text="Game Name:").grid(row=row_idx, column=0, sticky='w', **pad_opts)
        self.name_entry = tk.Entry(self.root)
        self.name_entry.grid(row=row_idx, column=1, sticky='ew', **pad_opts)
        row_idx += 1
        
        # Description
        tk.Label(self.root, text="Description:").grid(row=row_idx, column=0, sticky='w', **pad_opts)
        self.desc_entry = tk.Entry(self.root)
        self.desc_entry.grid(row=row_idx, column=1, sticky='ew', **pad_opts)
        row_idx += 1
        
        # Game Type
        tk.Label(self.root, text="Game Type:").grid(row=row_idx, column=0, sticky='w', **pad_opts)
        self.type_var = tk.StringVar(value="CLI")
        type_frame = tk.Frame(self.root)
        type_frame.grid(row=row_idx, column=1, sticky='w', **pad_opts)
        tk.Radiobutton(type_frame, text="CLI", variable=self.type_var, value="CLI").pack(side='left')
        tk.Radiobutton(type_frame, text="GUI", variable=self.type_var, value="GUI").pack(side='left')
        row_idx += 1
        
        # Version
        version_label = "Version:" if not self.current_version else f"Version (current: {self.current_version}):"
        tk.Label(self.root, text=version_label).grid(row=row_idx, column=0, sticky='w', **pad_opts)
        
        version_frame = tk.Frame(self.root)
        version_frame.grid(row=row_idx, column=1, sticky='w', **pad_opts)
        
        # Parse current version
        default_major, default_minor, default_patch = 1, 0, 0
        if self.current_version:
            try:
                parts = self.current_version.split(".")
                default_major = int(parts[0])
                default_minor = int(parts[1]) if len(parts) > 1 else 0
                default_patch = int(parts[2]) + 1 if len(parts) > 2 else 1
            except:
                pass
        
        self.major_var = tk.StringVar(value=str(default_major))
        self.minor_var = tk.StringVar(value=str(default_minor))
        self.patch_var = tk.StringVar(value=str(default_patch if self.current_version else 0))
        
        tk.Label(version_frame, text="Major:").pack(side='left')
        self.major_spinbox = ttk.Spinbox(version_frame, from_=0, to=999, width=5, textvariable=self.major_var)
        self.major_spinbox.pack(side='left', padx=(0, 10))
        
        tk.Label(version_frame, text="Minor:").pack(side='left')
        self.minor_spinbox = ttk.Spinbox(version_frame, from_=0, to=999, width=5, textvariable=self.minor_var)
        self.minor_spinbox.pack(side='left', padx=(0, 10))
        
        tk.Label(version_frame, text="Patch:").pack(side='left')
        self.patch_spinbox = ttk.Spinbox(version_frame, from_=0, to=999, width=5, textvariable=self.patch_var)
        self.patch_spinbox.pack(side='left')
        row_idx += 1
        
        # Min Players
        tk.Label(self.root, text="Min Players:").grid(row=row_idx, column=0, sticky='w', **pad_opts)
        self.min_players_spin = ttk.Spinbox(self.root, from_=1, to=99, width=10)
        self.min_players_spin.set(2)
        self.min_players_spin.grid(row=row_idx, column=1, sticky='w', **pad_opts)
        row_idx += 1

        # Max Players
        tk.Label(self.root, text="Max Players:").grid(row=row_idx, column=0, sticky='w', **pad_opts)
        self.max_players_spin = ttk.Spinbox(self.root, from_=1, to=99, width=10)
        self.max_players_spin.set(2)
        self.max_players_spin.grid(row=row_idx, column=1, sticky='w', **pad_opts)
        row_idx += 1
        
        # Path
        tk.Label(self.root, text="Game Directory Path:").grid(row=row_idx, column=0, sticky='w', **pad_opts)
        path_frame = tk.Frame(self.root)
        path_frame.grid(row=row_idx, column=1, sticky='ew', **pad_opts)
        
        self.path_entry = tk.Entry(path_frame)
        self.path_entry.pack(side='left', fill='x', expand=True)
        
        browse_btn = tk.Button(path_frame, text="Browse...", command=self._browse_path)
        browse_btn.pack(side='right', padx=(5, 0))
        row_idx += 1
        
        # Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.grid(row=row_idx, column=0, columnspan=2, pady=20, padx=10, sticky='ew')
        
        submit_btn = tk.Button(btn_frame, text="Upload", command=self._submit, bg='#4CAF50', fg='white')
        submit_btn.pack(side='right', padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=self._cancel)
        cancel_btn.pack(side='right', padx=5)

    def _browse_path(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, directory)
    
    def _parse_version(self, version_str):
        """Parse version string into tuple (major, minor, patch)"""
        try:
            parts = version_str.split(".")
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return (major, minor, patch)
        except:
            return (0, 0, 0)
    
    def _compare_versions(self, new_version, old_version):
        new = self._parse_version(new_version)
        old = self._parse_version(old_version)
        return new > old

    def _submit(self):
        name = self.name_entry.get().strip()
        description = self.desc_entry.get().strip()
        game_type = self.type_var.get()
        path = self.path_entry.get().strip()
        
        # Get version
        try:
            major = int(self.major_var.get())
            minor = int(self.minor_var.get())
            patch = int(self.patch_var.get())
            if major < 0 or minor < 0 or patch < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Version numbers must be non-negative integers.")
            return

        # Get player limits
        try:
            min_p = int(self.min_players_spin.get())
            max_p = int(self.max_players_spin.get())
            if min_p < 1:
                messagebox.showerror("Error", "Min players must be at least 1.")
                return
            if min_p > max_p:
                messagebox.showerror("Error", "Min players cannot be greater than Max players.")
                return
        except ValueError:
            messagebox.showerror("Error", "Player limits must be integers.")
            return
        
        version = f"{major}.{minor}.{patch}"
        
        # Validation
        if not name:
            messagebox.showerror("Error", "Game Name is required.")
            return
        if not path:
            messagebox.showerror("Error", "Game Directory Path is required.")
            return
        if not os.path.exists(path):
            messagebox.showerror("Error", "Selected path does not exist.")
            return
        if not os.path.isdir(path):
            messagebox.showerror("Error", "Selected path is not a directory.")
            return
        
        if self.current_version:
            if not self._compare_versions(version, self.current_version):
                messagebox.showerror("Error", f"New version ({version}) must be greater than current version ({self.current_version}).")
                return
            
        self.result = {
            "name": name,
            "description": description,
            "game_type": game_type,
            "version": version,
            "min_players": min_p,
            "max_players": max_p,
            "path": path
        }
        self.root.destroy()

    def _cancel(self):
        self.root.destroy()

    def show(self):
        self.root.mainloop()
        return self.result

if __name__ == "__main__":
    # Test
    dialog = GameUploadDialog(current_version="1.0.5")
    print(dialog.show())

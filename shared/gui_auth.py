import tkinter as tk
from tkinter import messagebox

class AuthDialog:
    def __init__(self, title="Login"):
        self.result = None
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("300x200")
        
        # Center the window
        self.root.eval('tk::PlaceWindow . center')
        
        self._create_widgets()
        
    def _create_widgets(self):
        pad_opts = {'padx': 10, 'pady': 5}
        
        # Username
        tk.Label(self.root, text="Username:").pack(anchor='w', **pad_opts)
        self.user_entry = tk.Entry(self.root)
        self.user_entry.pack(fill='x', **pad_opts)
        self.user_entry.focus_set()
        
        # Password
        tk.Label(self.root, text="Password:").pack(anchor='w', **pad_opts)
        self.pass_entry = tk.Entry(self.root, show="*")
        self.pass_entry.pack(fill='x', **pad_opts)
        self.pass_entry.bind('<Return>', self._submit)
        
        # Buttons
        btn_frame = tk.Frame(self.root, pady=10)
        btn_frame.pack(fill='x', padx=10)
        
        submit_btn = tk.Button(btn_frame, text="Submit", command=self._submit, bg='#4CAF50', fg='white')
        submit_btn.pack(side='right', padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=self._cancel)
        cancel_btn.pack(side='right', padx=5)

    def _submit(self, event=None):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        
        if not username:
            messagebox.showerror("Error", "Username is required.")
            return
        if not password:
            messagebox.showerror("Error", "Password is required.")
            return
            
        self.result = (username, password)
        self.root.destroy()

    def _cancel(self):
        self.root.destroy()

    def show(self):
        self.root.mainloop()
        return self.result

if __name__ == "__main__":
    # Test
    print(AuthDialog().show())

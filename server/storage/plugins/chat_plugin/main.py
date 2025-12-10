class Plugin:
    def __init__(self, context):
        self.context = context
        self.name = "Room Chat"

    def on_load(self):
        print(f"[{self.name}] Loaded!")

    def handle_input(self, text):
        if text.startswith("/chat "):
            msg = text[6:]
            self.context.send_plugin_message("chat_plugin", {"text": msg})
            return True
        return False

    def handle_message(self, payload, sender):
        if "text" in payload:
            print(f"[Chat] {sender}: {payload['text']}")

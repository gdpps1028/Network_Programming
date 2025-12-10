import json

# Message Types
MSG_LOGIN = "LOGIN"
MSG_REGISTER = "REGISTER"
MSG_UPLOAD_GAME = "UPLOAD_GAME"
MSG_UPDATE_GAME = "UPDATE_GAME"
MSG_REMOVE_GAME = "REMOVE_GAME"
MSG_LIST_GAMES = "LIST_GAMES"
MSG_GAME_DETAILS = "GAME_DETAILS"
MSG_DOWNLOAD_GAME = "DOWNLOAD_GAME"
MSG_CREATE_ROOM = "CREATE_ROOM"
MSG_JOIN_ROOM = "JOIN_ROOM"
MSG_LIST_ROOMS = "LIST_ROOMS"
MSG_START_GAME = "START_GAME"
MSG_GAME_STARTED = "GAME_STARTED"
MSG_GAME_OVER = "GAME_OVER"
MSG_SUBMIT_REVIEW = "SUBMIT_REVIEW"
MSG_LIST_REVIEWS = "LIST_REVIEWS"
MSG_LIST_PLUGINS = "LIST_PLUGINS"
MSG_DOWNLOAD_PLUGIN = "DOWNLOAD_PLUGIN"
MSG_PLUGIN_MESSAGE = "PLUGIN_MESSAGE"
MSG_LOGOUT = "LOGOUT"
MSG_ROOM_UPDATE = "ROOM_UPDATE"
MSG_LEAVE_ROOM = "LEAVE_ROOM"
MSG_CHAT = "CHAT"

# Response Status
STATUS_OK = "OK"
STATUS_ERROR = "ERROR"

# Roles
ROLE_DEVELOPER = "DEVELOPER"
ROLE_PLAYER = "PLAYER"

def create_message(msg_type, data=None):
    if data is None:
        data = {}
    return {
        "type": msg_type,
        "data": data
    }

def create_response(status, data=None, message=""):
    return {
        "status": status,
        "data": data if data else {},
        "message": message
    }

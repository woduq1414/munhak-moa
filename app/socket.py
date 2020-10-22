from flask import Flask
from flask_socketio import SocketIO
import socket
import os

hostname = socket.gethostname()
if hostname[:7] == "DESKTOP":
    socketio = SocketIO(ping_timeout=3, ping_interval=1)
else:
    socketio = SocketIO(ping_timeout=15, ping_interval=8)


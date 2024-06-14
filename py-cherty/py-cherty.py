import socket
import json
import base64

class Cherty:
    def __init__(self, host='127.0.0.1', port=1337):
        self.host = host
        self.port = port

    def checkpoint(self, data, metadata, identifier):
        # Convert data to base64 if it's binary
        if isinstance(data, bytes):
            data = base64.b64encode(data).decode('utf-8')

        message = {
            'data': data,
            'metadata': metadata,
            'identifier': identifier
        }

        self.send_message(message)

    def send_message(self, message):
        message_json = json.dumps(message)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((self.host, self.port))
            client_socket.sendall(message_json.encode('utf-8'))
        finally:
            client_socket.close()

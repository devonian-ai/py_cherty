import socket
import json
import base64
import os
import mimetypes
import csv

class Cherty:
    def __init__(self, host='127.0.0.1', port=1337):
        self.host = host
        self.port = port

    def checkpoint(self, data, metadata, identifier):
        data_type, local_path = self.evaluate_data(data)

        # Convert data to base64 if it's binary
        if data_type == 'binary':
            data = base64.b64encode(data).decode('utf-8')
        
        message = {
            'data': data,
            'metadata': metadata,
            'identifier': identifier,
            'localPath': local_path,
            'dataType': data_type
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

    def evaluate_data(self, data):
        # Check if data is a path to a file
        possible_path = os.path.abspath(data)
        if os.path.isfile(possible_path):
            mime_type, _ = mimetypes.guess_type(possible_path)
            return (mime_type or 'binary', possible_path)

        # Check if data is bytes
        if isinstance(data, bytes):
            return ('binary', None)

        # Check if data is a string and try to identify the type
        try:
            if isinstance(data, str):
                # Check if it's a valid JSON
                try:
                    json.loads(data)
                    return ('json', None)
                except json.JSONDecodeError:
                    pass

                # Check if it's a CSV by trying to parse the first few lines
                try:
                    csv.Sniffer().sniff(data)
                    return ('csv', None)
                except csv.Error:
                    pass
                
                return ('text', None)
        except Exception as e:
            print(f"Error in evaluating data type: {e}")
        
        return ('unknown', None)

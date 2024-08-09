import socket
import json
import base64
import io
import os
import mimetypes
import csv
import zarr
import tempfile

class Cherty:
    def __init__(self, host='127.0.0.1', port=1337):
        self.host = host
        self.port = port

    def checkpoint(self, data, metadata, identifier):
        # Convert dict to JSON string if data is a dictionary
        if isinstance(data, dict):
            data = json.dumps(data)
            data_type = 'json'
            local_path = None
        elif hasattr(data, 'to_zarr'):
            # Create a named temporary file to store the ZipStore
            with tempfile.NamedTemporaryFile() as temp_file:
                store = zarr.ZipStore(temp_file.name, mode='w')  # Use ZipStore with the temporary file
                data.to_zarr(store=store)
                store.close()  # Ensure all data is written

                # Read the content of the temporary file into a buffer
                temp_file.seek(0)
                binary_data = temp_file.read()

            # Encode the binary data in base64
            data = base64.b64encode(binary_data).decode('utf-8')
            data_type = 'application/x-zarr'
            local_path = None
        else:
            data_type, local_path = self.evaluate_data(data)

        # Convert data to base64 if it's binary
        if data_type == 'binary':
            data = base64.b64encode(data).decode('utf-8')
        
        message = {
            'data': data,
            'metadata': metadata,
            'identifier': identifier,
            'localPath': local_path if 'local_path' in locals() else None,
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
        try:
            possible_path = os.path.abspath(data)
            if os.path.isfile(possible_path):
                mime_type, _ = mimetypes.guess_type(possible_path)
                return (mime_type or 'binary', possible_path)
        except Exception as e:
            print(f"Error in evaluating file path: {e}")

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
                    # A CSV should have multiple rows and columns, so we do a more thorough check
                    dialect = csv.Sniffer().sniff(data)
                    # Split the data into lines and check if it has multiple lines with the delimiter
                    lines = data.splitlines()
                    if len(lines) > 1 and all(dialect.delimiter in line for line in lines):
                        return ('csv', None)
                except csv.Error:
                    pass
                
                # Default to plain text
                return ('text/plain', None)
        except Exception as e:
            print(f"Error in evaluating data type: {e}")
        
        return ('unknown', None)

# # Example usage
# if __name__ == "__main__":
#     cherty = Cherty()
#     cherty.checkpoint("Hello, world!", {"type": "greeting"}, "#example_1")
#     cherty.checkpoint("name,age\nAlice,30\nBob,25", {"type": "csv_data"}, "#example_2")
#     cherty.checkpoint({"msg": "Hello from Python"}, {"type": "json_data"}, "#example_3")
#     cherty.checkpoint("Hello from Python", {"type": "text"}, "#trffl_6loqBNGg")

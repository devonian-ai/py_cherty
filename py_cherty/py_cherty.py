import socket
import json
import base64
import io
import os
import mimetypes
import csv
import tempfile
import zarr
import pandas as pd
import hashlib

class Cherty:
    def __init__(self, host='127.0.0.1', port=1337):
        self.host = host
        self.port = port

    # extension is optional; required to correctly interpret binary data
    def checkpoint(self, data, metadata, identifier, extension=None):

        # Figure out what type of data is being sent
        # local_is_temp is a flag to indicate if the file is temporary and should be deleted after sending
        data, data_type, local_path, local_is_temp = self.evaluate_data(data, extension)
        
        # The data is either (1) base64 encoded, so it can be sent as a string
        # or (2) a path to a file, so it can also be sent as a string
        message = {
            'data': data,
            'metadata': metadata,
            'identifier': identifier,
            'localPath': local_path if 'local_path' in locals() else None,
            'localIsTemp': local_is_temp,
            'dataType': data_type,
            'extension': extension
        }

        # Convert the message to a JSON string
        message_str = json.dumps(message)

        # Prefix with the length of the message
        message_len = f"{len(message_str):<10}"  # Fixed-width length field

        # Send the length-prefixed message
        self.send_message(message_len + message_str)

    def send_message(self, message):
        message_json = json.dumps(message)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((self.host, self.port))
            client_socket.sendall(message_json.encode('utf-8'))
        finally:
            client_socket.close()

    def evaluate_data(self, data, extension):

        # Check if data is a path to a file. In this case, transmit the path over IPC
        try:
            possible_path = os.path.abspath(data)
            if os.path.isfile(possible_path):
                mime_type, _ = mimetypes.guess_type(possible_path)
                return (data, mime_type or 'binary', possible_path, False)
        except Exception as e:
            # print(f"Error in evaluating data as file path: {e}")
            pass

        # Convert dict to JSON string if data is a dictionary
        # Send directly if below 100 MB, otherwise send as a temp file
        if isinstance(data, dict):
            data = json.dumps(data)
            data_type = 'application/json'
            size_in_bytes = len(data.encode('utf-8'))
            data, local_path, is_temp = self.size_switch(size_in_bytes, data, '.json')
            return (data, data_type, local_path, is_temp)
        
        # For xarray datasets, save as temporary Zarr file
        elif hasattr(data, 'to_zarr'):
            data, data_type, local_path, is_temp = self.store_as_netcdf(data)
            return (data, data_type, local_path, is_temp)
        
        # Check if data is bytes
        elif isinstance(data, bytes):
            data_type = 'application/octet-stream'
            size_in_bytes = len(data)
            data, local_path, is_temp = self.size_switch(size_in_bytes, data, '.bin')
            return (data, data_type, local_path, is_temp)
        # If it's a pandas df, convert to a csv string
        elif isinstance(data, pd.DataFrame):
            data = data.to_csv(index=False)
        
        # Check if data is a string and try to identify the type
        try:
            if isinstance(data, str):
                # Check if it's a valid JSON
                try:
                    parsed_data = json.loads(data)
                    return self.evaluate_data(parsed_data, '.json')
                except json.JSONDecodeError:
                    pass

                # Check if it's a CSV by trying to parse the first few lines
                try:
                    # A CSV should have multiple rows and columns, so we do a more thorough check
                    dialect = csv.Sniffer().sniff(data)
                    # Split the data into lines and check if it has multiple lines with the delimiter
                    lines = data.splitlines()
                    if len(lines) > 1 and all(dialect.delimiter in line for line in lines):
                        size_in_bytes = len(data)
                        data_type = 'text/csv'
                        data, local_path, is_temp = self.size_switch(size_in_bytes, data, '.csv')
                        return (data, data_type, local_path, is_temp)
                except csv.Error:
                    pass
                
                # Default to plain text
                size_in_bytes = len(data)
                data, local_path, is_temp = self.size_switch(size_in_bytes, data, '.txt')
                data_type = 'text/plain'
                return (data, data_type, local_path, is_temp)
        except Exception as e:
            print(f"Error in evaluating data type: {e}")
        
        try:
            data_as_bytes = bytes(data, 'utf-8')
            return self.evaluate_data(data_as_bytes, extension)
        except:
            pass
        return (data, None, None, None)

    def size_switch (self, size_in_bytes, data, extension):
        if size_in_bytes < 75 * 1024 * 1024:  # 75 MB
            if isinstance(data, (bytes, bytearray)):
                data = base64.b64encode(data).decode('utf-8') # Convert to base64 so it can be sent as ASCII
            local_path = None
            is_temp = False
        else:
            local_path = self.save_temp_data(data, extension)
            data = None
            is_temp = True
        return (data, local_path, is_temp)

    def save_temp_data(self, data, extension):

        # Create a temporary file that won't be deleted automatically
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
        try:
            if not isinstance(data, (bytes, bytearray)):
                data = data.encode('utf-8') 
            temp_file.write(data)
            temp_file_path = temp_file.name  # Get the path to the file
            # print(f"Temporary file created at: {temp_file_path}")
        finally:
            temp_file.close()  # Close the file, but it won't be deleted

        return temp_file_path


    def store_as_netcdf(self, data):
        # Create a named temporary file with .nc extension and ensure it is not deleted automatically
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.nc')
        
        try:
            # Save the xarray Dataset to NetCDF format
            data.to_netcdf(temp_file.name)

            # Calculate the hash of the file
            with open(temp_file.name, 'rb') as f:
                file_data = f.read()
                data_hash = hashlib.sha256(file_data).hexdigest()
            # print(f"Data SHA-256 Hash: {data_hash}")

            # Save the path of the temporary file
            temp_file_path = temp_file.name
            # print(f"Temporary file created at: {temp_file_path}")
        finally:
            temp_file.close()  # Close the file, but it won't be deleted

        # Return metadata for further use
        data = None
        data_type = 'application/x-netcdf'
        local_path = temp_file_path
        is_temp = True
        return (data, data_type, local_path, is_temp)

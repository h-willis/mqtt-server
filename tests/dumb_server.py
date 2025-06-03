import socket

HOST = '127.0.0.1'  # or '' to accept all interfaces
PORT = 1883        # make sure this matches what the client uses

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)  # 1 = max number of queued connections
print(f"Listening on {HOST}:{PORT}...")

conn, addr = server_socket.accept()
print(f"Connected by {addr}")
while True:
    pass

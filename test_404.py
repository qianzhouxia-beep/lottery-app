import socket, urllib.parse

# Send a raw HTTP request to see what path the server receives
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
s.connect(('localhost', 5123))
req = b'GET /api/predict_ai?kind=dlt&fc=5&bc=2 HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n'
s.sendall(req)
resp = s.recv(4096)
print(repr(resp[:300]))
s.close()
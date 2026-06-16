import socket

tests = [
    b'GET /api/predict_ai?kind=dlt HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n',
    b'GET /api/predict_ai HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n',
    b'GET /api/predict HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n',
]

for req in tests:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(('localhost', 5123))
    s.sendall(req)
    resp = s.recv(2048)
    status = resp.split(b'\r\n')[0]
    body = resp.split(b'\r\n\r\n', 1)[1][:80]
    print(f'{req[:40]} -> {status} | {body}')
    s.close()
"""Debug test for HTTP server."""
import socket

# Создаем тестовый запрос
request = b"GET / HTTP/1.1\r\nHost: localhost:8080\r\nUser-Agent: curl/8.7.1\r\nAccept: */*\r\n\r\n"

print(f"Request length: {len(request)}")
print(f"Request: {request!r}")

# Отправляем запрос
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 8080))
sock.sendall(request)

# Получаем ответ
response = b''
while True:
    try:
        sock.settimeout(2.0)
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk
        if b'\r\n\r\n' in response:
            # Проверяем Content-Length
            header_part = response.split(b'\r\n\r\n', 1)[0].decode('utf-8', errors='replace')
            if 'Content-Length:' in header_part:
                for line in header_part.split('\r\n'):
                    if line.startswith('Content-Length:'):
                        cl = int(line.split(':')[1].strip())
                        body_part = response.split(b'\r\n\r\n', 1)[1] if b'\r\n\r\n' in response else b''
                        if len(body_part) >= cl:
                            break
    except socket.timeout:
        break

print(f"\nResponse length: {len(response)}")
print(f"Response:\n{response.decode('utf-8', errors='replace')}")
sock.close()

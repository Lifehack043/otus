"""Simple debug test - direct socket test."""
import socket

# Создаем сервер для теста
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('127.0.0.1', 8888))
server.listen(1)
server.setblocking(False)

import select

# Ждем подключения
readable, _, _ = select.select([server], [], [], 5)
if readable:
    client, addr = server.accept()
    client.setblocking(False)
    print(f"Client connected from {addr}")
    
    # Ждем данные
    buffer = b''
    while b'\r\n\r\n' not in buffer:
        readable, _, _ = select.select([client], [], [], 5)
        if not readable:
            print("Timeout waiting for data")
            break
        
        while True:
            try:
                data = client.recv(4096)
                if not data:
                    print("Client disconnected")
                    break
                print(f"Received {len(data)} bytes: {data!r}")
                buffer += data
                if b'\r\n\r\n' in buffer:
                    break
            except BlockingIOError:
                break
    
    print(f"\nFull buffer ({len(buffer)} bytes):")
    print(buffer.decode('utf-8', errors='replace'))
    
    # Отправляем ответ
    response = "HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\nHello, World!"
    client.sendall(response.encode())
    client.close()

server.close()

"""
HTTP сервер с асинхронной обработкой на основе epoll (Linux) / select (macOS).

Поддерживает:
- GET и HEAD запросы
- Возврат статических файлов из DOCUMENT_ROOT
- Корректные HTTP заголовки (Date, Server, Content-Length,
  Content-Type, Connection)
- URL decoding (%XX кодировка)
- Масштабирование на несколько worker'ов (-w)
- DOCUMENT_ROOT задается через -r

Пример запуска:
    python3 httpd.py -r ./www -p 8080
    python3 httpd.py -r ./www -p 8080 -w 4

Архитектура:
- Asynchronous event loop с epoll (Linux) / select (macOS/fallback)
- Каждый запрос обрабатывается в отдельном потоке после получения
  полного заголовка
- Thread-safe обработка соединений
"""

import socket
import select
import os
import sys
import argparse
import threading
import time
import urllib.parse
from datetime import datetime, timezone


# Маппинг расширений файлов на Content-Type
CONTENT_TYPES = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.swf': 'application/x-shockwave-flash',
}

DEFAULT_CONTENT_TYPE = 'application/octet-stream'

# Размер буфера для чтения/записи
BUFFER_SIZE = 65536

# Максимальный размер заголовков запроса
MAX_HEADERS_SIZE = 8192


def get_content_type(file_path):
    """Определяет Content-Type на основе расширения файла."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    return CONTENT_TYPES.get(ext, DEFAULT_CONTENT_TYPE)


def format_date(dt=None):
    """Форматирует дату в формате HTTP (RFC 7231)."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')


def url_decode(path):
    """Декодирует URL-кодированный путь (%XX -> символ)."""
    return urllib.parse.unquote(path)


def parse_request(data):
    """
    Парсит HTTP-запрос и возвращает метод, путь и заголовки.

    Returns:
        tuple: (method, path, headers_dict) или None при ошибке
    """
    try:
        if '\r\n\r\n' not in data:
            return None

        header_part = data.split('\r\n\r\n', 1)[0]
        lines = header_part.split('\r\n')
        if not lines:
            return None

        request_line = lines[0]
        parts = request_line.split(' ')
        if len(parts) < 2:
            return None

        method = parts[0]
        path = parts[1]

        headers = {}
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()

        return method, path, headers
    except Exception:
        return None


def build_response(status_code, status_text, headers, body=None):
    """
    Строит HTTP-ответ.

    Args:
        status_code: Код статуса (200, 404, etc.)
        status_text: Текст статуса (OK, Not Found, etc.)
        headers: Словарь заголовков
        body: Тело ответа (bytes или None)

    Returns:
        bytes: Сформированный HTTP-ответ
    """
    response = f'HTTP/1.1 {status_code} {status_text}\r\n'

    if body:
        headers['Content-Length'] = str(len(body))

    for key, value in headers.items():
        response += f'{key}: {value}\r\n'

    response += '\r\n'

    result = response.encode('utf-8')
    if body:
        result += body

    return result


def send_response(
        client_socket, status_code, status_text, headers, body=None
):
    """Отправляет HTTP-ответ клиенту."""
    if headers is None:
        headers = {}

    response_headers = {
        'Date': format_date(),
        'Server': 'PythonHTTPD/1.0',
        'Connection': 'close',
    }
    response_headers.update(headers)

    response = build_response(status_code, status_text, response_headers, body)

    # Переключаем сокет в блокирующий режим для надёжной
    # отправки больших ответов (неблокирующий сокет
    # может не отправить все данные за один вызов)
    client_socket.setblocking(True)
    client_socket.sendall(response)


def process_request(client_socket, document_root, buffer):
    """
    Обрабатывает HTTP-запрос (вызывается в отдельном потоке).

    Args:
        client_socket: Сокет клиента
        document_root: Путь к корневой директории
        buffer: Буфер с данными запроса
    """
    try:
        # Парсим запрос из буфера
        header_str = buffer.decode('utf-8', errors='replace')
        parsed = parse_request(header_str)

        if not parsed:
            send_response(client_socket, 400, 'Bad Request', None)
            return

        method, path, headers = parsed

        # Поддержка только GET и HEAD
        if method not in ('GET', 'HEAD'):
            send_response(client_socket, 405, 'Method Not Allowed', None)
            return

        # Декодируем путь
        path = url_decode(path)

        # Обработка query string - удаляем
        if '?' in path:
            path = path.split('?')[0]

        # Обработка корневого пути
        if path == '/':
            path = '/index.html'

        # Проверка на directory traversal
        # Проверяем только паттерны ../ и /.., но не двойные точки
        # в именах файлов (например text..txt)
        if '/..' in path or path.endswith('..'):
            send_response(client_socket, 403, 'Forbidden', None)
            return

        # Формируем полный путь к файлу
        file_path = os.path.normpath(
            os.path.join(document_root, path.lstrip('/'))
        )

        # Проверка что файл находится внутри document_root
        norm_root = os.path.normpath(document_root)
        if not (file_path.startswith(norm_root + os.sep) or
                file_path == norm_root):
            send_response(client_socket, 403, 'Forbidden', None)
            return

        # Проверка существования файла
        if not os.path.exists(file_path):
            send_response(client_socket, 404, 'Not Found', None)
            return

        # Если путь заканчивается на /, это должна быть директория
        if path.endswith('/') and not os.path.isdir(file_path):
            send_response(client_socket, 404, 'Not Found', None)
            return

        # Проверка что это файл (а не директория)
        if os.path.isdir(file_path):
            # Пытаемся найти index.html в директории
            index_path = os.path.join(file_path, 'index.html')
            if os.path.isfile(index_path):
                file_path = index_path
            else:
                send_response(client_socket, 404, 'Not Found', None)
                return

        # Проверка на читаемость файла
        if not os.access(file_path, os.R_OK):
            send_response(client_socket, 403, 'Forbidden', None)
            return

        # Читаем файл
        with open(file_path, 'rb') as f:
            body = f.read()

        # Определяем Content-Type
        content_type = get_content_type(file_path)

        # Формируем заголовки
        response_headers = {
            'Content-Type': content_type,
        }

        if method == 'HEAD':
            # Для HEAD возвращаем только заголовки
            response_headers['Content-Length'] = str(len(body))
            body = None

        send_response(client_socket, 200, 'OK', response_headers, body)

    except Exception:
        try:
            send_response(client_socket, 500, 'Internal Server Error', None)
        except Exception:
            pass
    finally:
        try:
            client_socket.close()
        except Exception:
            pass


class AsyncHTTPServer:
    """
    Асинхронный HTTP-сервер.

    Использует epoll (Linux) или select (macOS/fallback)
    для эффективной обработки множества соединений.
    """

    def __init__(self, host, port, document_root):
        self.host = host
        self.port = port
        self.document_root = document_root
        self.server_socket = None
        self.running = False
        # Словарь: fileno -> {'socket': socket, 'buffer': bytes}
        self.clients = {}
        # Определяем доступный backend
        self.backend = self._detect_backend()

    def _detect_backend(self):
        """Определяет доступный backend для event loop."""
        if hasattr(select, 'epoll') and sys.platform == 'linux':
            return 'epoll'
        else:
            return 'select'

    def start(self):
        """Запускает сервер."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )

        try:
            self.server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEPORT, 1
            )
        except (AttributeError, OSError):
            pass

        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1024)
        self.server_socket.setblocking(False)

        self.running = True
        print(f'HTTP сервер запущен на {self.host}:{self.port}')
        print(f'DOCUMENT_ROOT: {self.document_root}')
        print(f'Backend: {self.backend}')

        try:
            if self.backend == 'epoll':
                self._run_epoll()
            else:
                self._run_select()
        except KeyboardInterrupt:
            print('\nОстановка сервера...')
        finally:
            self.stop()

    def _run_epoll(self):
        """Event loop на основе epoll (Linux)."""
        epoll = select.epoll()
        epoll.register(self.server_socket.fileno(),
                       select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP)

        try:
            while self.running:
                try:
                    events = epoll.poll(1)
                except OSError:
                    break

                for fileno, event in events:
                    if fileno == self.server_socket.fileno():
                        self._accept_connections_epoll(epoll)
                    elif fileno in self.clients:
                        if event & (select.EPOLLERR | select.EPOLLHUP):
                            self._close_client_epoll(epoll, fileno)
                        else:
                            self._read_client_epoll(epoll, fileno)
        finally:
            epoll.close()

    def _run_select(self):
        """Event loop на основе select (macOS/fallback)."""
        read_fds = [self.server_socket.fileno()]

        while self.running:
            try:
                readable, _, errored = select.select(read_fds, [], read_fds, 1)
            except (ValueError, OSError):
                break

            for fileno in errored:
                if fileno in self.clients:
                    self._close_client_select(fileno, read_fds)

            for fileno in readable:
                if fileno == self.server_socket.fileno():
                    self._accept_connections_select(read_fds)
                elif fileno in self.clients:
                    self._read_client_select(fileno, read_fds)

    # --- Epoll methods ---

    def _accept_connections_epoll(self, epoll):
        """Принимает новые подключения (epoll)."""
        while True:
            try:
                client_socket, addr = self.server_socket.accept()
                client_socket.setblocking(False)
                fileno = client_socket.fileno()

                epoll.register(fileno, select.EPOLLIN)
                self.clients[fileno] = {'socket': client_socket, 'buffer': b''}
            except BlockingIOError:
                break
            except OSError:
                break

    def _read_client_epoll(self, epoll, fileno):
        """Читает данные от клиента (epoll)."""
        client_info = self.clients.get(fileno)
        if not client_info:
            return

        client_socket = client_info['socket']

        try:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                self._close_client_epoll(epoll, fileno)
                return

            client_info['buffer'] += data

            if len(client_info['buffer']) > MAX_HEADERS_SIZE:
                send_response(client_socket, 413, 'Payload Too Large', None)
                self._close_client_epoll(epoll, fileno)
                return

            if b'\r\n\r\n' in client_info['buffer']:
                epoll.unregister(fileno)
                self.clients.pop(fileno, None)
                self._handle_request(client_socket, client_info['buffer'])
        except Exception:
            self._close_client_epoll(epoll, fileno)

    def _close_client_epoll(self, epoll, fileno):
        """Закрывает соединение (epoll)."""
        client_info = self.clients.pop(fileno, None)
        if client_info:
            try:
                epoll.unregister(fileno)
            except Exception:
                pass
            try:
                client_info['socket'].close()
            except Exception:
                pass

    # --- Select methods ---

    def _accept_connections_select(self, read_fds):
        """Принимает новые подключения (select)."""
        while True:
            try:
                client_socket, addr = self.server_socket.accept()
                client_socket.setblocking(False)
                fileno = client_socket.fileno()

                read_fds.append(fileno)
                self.clients[fileno] = {'socket': client_socket, 'buffer': b''}
            except BlockingIOError:
                break
            except OSError:
                break

    def _read_client_select(self, fileno, read_fds):
        """Читает данные от клиента (select)."""
        client_info = self.clients.get(fileno)
        if not client_info:
            return

        client_socket = client_info['socket']

        try:
            # Читаем все доступные данные в неблокирующем режиме
            while True:
                try:
                    data = client_socket.recv(BUFFER_SIZE)
                    if not data:
                        self._close_client_select(fileno, read_fds)
                        return
                    client_info['buffer'] += data

                    if len(client_info['buffer']) > MAX_HEADERS_SIZE:
                        send_response(
                            client_socket, 413, 'Payload Too Large', None
                        )
                        self._close_client_select(fileno, read_fds)
                        return

                    if b'\r\n\r\n' in client_info['buffer']:
                        if fileno in read_fds:
                            read_fds.remove(fileno)
                        self.clients.pop(fileno, None)
                        self._handle_request(
                            client_socket, client_info['buffer']
                        )
                        return
                except BlockingIOError:
                    # Нет больше данных, ждем следующего события select
                    return
                except OSError:
                    self._close_client_select(fileno, read_fds)
                    return
        except Exception:
            self._close_client_select(fileno, read_fds)

    def _close_client_select(self, fileno, read_fds):
        """Закрывает соединение (select)."""
        client_info = self.clients.pop(fileno, None)
        if client_info:
            if fileno in read_fds:
                read_fds.remove(fileno)
            try:
                client_info['socket'].close()
            except Exception:
                pass

    # --- Common methods ---

    def _handle_request(self, client_socket, buffer):
        """Обрабатывает запрос в отдельном потоке."""
        thread = threading.Thread(
            target=process_request,
            args=(client_socket, self.document_root, buffer)
        )
        thread.daemon = True
        thread.start()

    def stop(self):
        """Останавливает сервер."""
        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

        for fileno, client_info in self.clients.items():
            try:
                client_info['socket'].close()
            except Exception:
                pass
        self.clients.clear()


def run_worker(host, port, document_root):
    """Запускает worker (в отдельном потоке)."""
    server = AsyncHTTPServer(host, port, document_root)
    server.start()


def main():
    """Точка входа в приложение."""
    parser = argparse.ArgumentParser(
        description='HTTP сервер на Python с асинхронной обработкой'
    )
    parser.add_argument(
        '-r', '--root', default='./www',
        help='Корневая директория для документов (по умолчанию: ./www)'
    )
    parser.add_argument(
        '-p', '--port', type=int, default=8080,
        help='Порт для прослушивания (по умолчанию: 8080)'
    )
    parser.add_argument(
        '-w', '--workers', type=int, default=1,
        help='Количество worker-ов (по умолчанию: 1)'
    )
    parser.add_argument(
        '-b', '--bind', default='0.0.0.0',
        help='Адрес для привязки (по умолчанию: 0.0.0.0)'
    )

    args = parser.parse_args()

    # Проверяем существование DOCUMENT_ROOT
    if not os.path.isdir(args.root):
        print(f'Ошибка: директория {args.root} не существует')
        sys.exit(1)

    document_root = os.path.abspath(args.root)

    if args.workers == 1:
        # Запускаем одиночный сервер
        server = AsyncHTTPServer(args.bind, args.port, document_root)
        server.start()
    else:
        # Запускаем несколько worker-ов
        print(f'Запуск {args.workers} worker-ов...')
        threads = []
        for i in range(args.workers):
            t = threading.Thread(
                target=run_worker,
                args=(args.bind, args.port, document_root),
                daemon=True
            )
            t.start()
            threads.append(t)
            print(f'Worker {i + 1} запущен')

        try:
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            print('\nОстановка сервера...')


if __name__ == '__main__':
    main()

# HTTP Server

Асинхронный HTTP-сервер на Python, частично реализующий протокол HTTP.

## Архитектура

Сервер использует **асинхронную архитектуру на основе event loop** с обработкой соединений через:

- **epoll** на Linux (высокоэффективный I/O multiplexing)
- **select** на macOS и других системах (fallback)

После получения полного HTTP-заголовка, обработка запроса делегируется в отдельный поток (`threading`), что позволяет эффективно использовать CPU для чтения файлов и формирования ответов, не блокируя event loop.

### Ключевые компоненты:

- [`AsyncHTTPServer`](httpd.py:256) — основной класс сервера с event loop
- [`process_request()`](httpd.py:154) — функция обработки запроса в отдельном потоке
- [`parse_request()`](httpd.py:73) — парсер HTTP-запросов
- [`build_response()`](httpd.py:108) — конструктор HTTP-ответов

### Поддержка множественных worker'ов

Сервер поддерживает запуск нескольких worker'ов через аргумент `-w`, каждый worker работает в отдельном потоке и использует `SO_REUSEPORT` для распределения соединений.

## Установка

Требования:
- Python 3.6+
- Стандартная библиотека (дополнительные пакеты не требуются)

## Запуск

```bash
# Базовый запуск
python3 httpd.py -r ./www -p 8080

# С несколькими worker'ами
python3 httpd.py -r ./www -p 8080 -w 4

# На другом порту и адресе
python3 httpd.py -r ./www -p 3000 -b 127.0.0.1
```

### Аргументы командной строки:

| Аргумент | Описание | По умолчанию |
|----------|----------|--------------|
| `-r, --root` | Корневая директория для документов | `./www` |
| `-p, --port` | Порт для прослушивания | `8080` |
| `-w, --workers` | Количество worker'ов | `1` |
| `-b, --bind` | Адрес для привязки | `0.0.0.0` |

## Реализованный функционал

### HTTP-методы
- **GET** — возврат файлов
- **HEAD** — возврат заголовков без тела
- Прочие методы — ответ **405 Method Not Allowed**

### Коды ответов
- **200 OK** — успешный запрос
- **400 Bad Request** — некорректный запрос
- **403 Forbidden** — доступ запрещён (directory traversal, нет прав на чтение)
- **404 Not Found** — файл не найден
- **405 Method Not Allowed** — неподдерживаемый метод
- **413 Payload Too Large** — заголовки превышают максимальный размер
- **500 Internal Server Error** — внутренняя ошибка сервера

### Поддерживаемые Content-Type

| Расширение | Content-Type |
|------------|--------------|
| `.html` | `text/html` |
| `.css` | `text/css` |
| `.js` | `application/javascript` |
| `.jpg`, `.jpeg` | `image/jpeg` |
| `.png` | `image/png` |
| `.gif` | `image/gif` |
| `.swf` | `application/x-shockwave-flash` |
| другое | `application/octet-stream` |

### Заголовки ответов
- `Date` — текущее время в формате RFC 7231
- `Server` — `PythonHTTPD/1.0`
- `Content-Length` — размер тела ответа
- `Content-Type` — тип контента на основе расширения файла
- `Connection` — `close`

### Особенности
- URL-декодирование (`%XX` кодировка)
- Поддержка пробелов в именах файлов
- Защита от directory traversal (`..`)
- Автоматический возврат `index.html` для директорий
- Проверка что файл находится внутри DOCUMENT_ROOT

## Нагрузочное тестирование

### Команда

```bash
ab -n 50000 -c 100 -r http://127.0.0.1:8080/
```

> **Примечание:** на macOS используется `127.0.0.1` вместо `localhost`,
> так как `localhost` может резолвиться в IPv6 `::1`, что вызывает
> ошибки `apr_socket_connect(): Operation already in progress`.

### Результаты

```
Server Software:        PythonHTTPD/1.0
Server Hostname:        127.0.0.1
Server Port:            8080

Document Path:          /
Document Length:        736 bytes

Concurrency Level:      100
Time taken for tests:   9.044 seconds
Complete requests:      50000
Failed requests:        0

Requests per second:    5528.69 [#/sec] (mean)
Time per request:       18.087 [ms] (mean)
Time per request:       0.181 [ms] (mean, across all concurrent requests)
Transfer rate:          4762.02 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   1.1      0      45
Processing:     0   18  12.9     16     254
Waiting:        0   18  12.9     16     254
Total:          0   18  12.8     16     254

Percentage of the requests served within a certain time (ms)
  50%     16
  66%     17
  75%     18
  80%     18
  90%     23
  95%     36
  98%     59
  99%     78
 100%    254 (longest request)
```

### Ключевые показатели

| Метрика | Значение |
|---------|----------|
| Запросов в секунду | **5528.69 req/sec** |
| Среднее время запроса | 18.087 ms |
| Ошибок | **0** |
| Пропускная способность | 4762.02 KB/sec |
| Медиана времени ответа | 16 ms |
| 95-й перцентиль | 36 ms |
| 99-й перцентиль | 78 ms |

### Тест с меньшей нагрузкой (10 concurrent)

```
Concurrency Level:      10
Complete requests:      5000
Failed requests:        0
Requests per second:    6453.99 [#/sec] (mean)
Time per request:       1.549 [ms] (mean)
```

## Тесты http-test-suite

Используется тестовый набор:
https://github.com/s-stupnikov/http-test-suite

### Результаты

```
Ran 23 tests in 0.066s

OK
```

Все **23 теста пройдены успешно**:

| Тест | Описание | Статус |
|------|----------|--------|
| test_directory_index | directory index file exists | ✅ |
| test_document_root_escaping | document root escaping forbidden | ✅ |
| test_empty_request | Send bad http headers | ✅ |
| test_file_in_nested_folders | file located in nested folders | ✅ |
| test_absent_file | absent file returns 404 | ✅ |
| test_file_urlencoded | urlencoded filename | ✅ |
| test_file_with_dot_in_name | file with two dots in name | ✅ |
| test_file_with_query_string | query string after filename | ✅ |
| test_file_with_slash | slash after filename | ✅ |
| test_file_with_spaces | filename with spaces | ✅ |
| test_content_type_css | Content-Type for .css | ✅ |
| test_content_type_gif | Content-Type for .gif | ✅ |
| test_content_type_html | Content-Type for .html | ✅ |
| test_content_type_jpeg | Content-Type for .jpeg | ✅ |
| test_content_type_jpg | Content-Type for .jpg | ✅ |
| test_content_type_js | Content-Type for .js | ✅ |
| test_content_type_png | Content-Type for .png | ✅ |
| test_content_type_swf | Content-Type for .swf | ✅ |
| test_head_method | head method support | ✅ |
| test_directory_index_absent | directory index file absent | ✅ |
| test_large_file | large file downloaded correctly | ✅ |
| test_post_method | post method forbidden | ✅ |
| test_server_header | Server header exists | ✅ |

### Как запустить тесты

```bash
# Скопировать httptest в DOCUMENT_ROOT
cp -r http-test-suite/httptest ./www/

# Запустить сервер
python3 httpd.py -r ./www -p 8080

# Запустить тесты
cd http-test-suite
python3 -c "
import sys; sys.argv = ['httptest.py']
exec(open('httptest.py').read().replace('port = 80', 'port = 8080'))
"
```

## Структура проекта

```
.
├── httpd.py              # Основной файл сервера (точка входа)
├── README.md             # Этот файл
├── www/                  # DOCUMENT_ROOT (тестовые файлы)
│   ├── index.html
│   ├── file.html
│   ├── style.css
│   ├── app.js
│   ├── test file.html
│   ├── test.gif
│   ├── test.jpg
│   ├── test.png
│   └── directory/
│       └── index.html
└── homework_skeleton.py  # Исходный шаблон (если был)
```

## Примечания

- На macOS `SO_REUSEPORT` может работать некорректно. Для тестирования множественных worker'ов рекомендуется использовать Linux (например, CentOS 7 в контейнере).
- Сервер не использует сторонние HTTP-библиотеки — вся обработка протокола реализована самостоятельно через работу с сокетами.

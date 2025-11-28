#!/usr/bin/env python3
import re
import sys
import statistics
import gzip
import os
from collections import defaultdict
import argparse


def detect_file_type(file_path):
    """
    Определяет тип файла: обычный текст или gzip
    """
    with open(file_path, 'rb') as f:
        magic_number = f.read(2)
        return 'gzip' if magic_number == b'\x1f\x8b' else 'text'


def open_log_file(log_file_path):
    """
    Открывает файл логов, автоматически определяя сжатие
    """
    file_type = detect_file_type(log_file_path)

    if file_type == 'gzip':
        return gzip.open(log_file_path, 'rt', encoding='utf-8')
    else:
        return open(log_file_path, 'r', encoding='utf-8')


def parse_log_file(log_file_path):
    """
    Парсит лог файл nginx в формате ui_short
    """
    # Регулярное выражение для парсинга строки лога
    log_pattern = re.compile(
        r'(?P<remote_addr>\S+)\s+'
        r'(?P<remote_user>\S+)\s+'
        r'(?P<http_x_real_ip>\S+)\s+'
        r'\[(?P<time_local>[^\]]+)\]\s+'
        r'"(?P<request>[^"]*)"\s+'
        r'(?P<status>\d+)\s+'
        r'(?P<body_bytes_sent>\d+)\s+'
        r'"(?P<http_referer>[^"]*)"\s+'
        r'"(?P<http_user_agent>[^"]*)"\s+'
        r'"(?P<http_x_forwarded_for>[^"]*)"\s+'
        r'"(?P<http_X_REQUEST_ID>[^"]*)"\s+'
        r'"(?P<http_X_RB_USER>[^"]*)"\s+'
        r'(?P<request_time>\d+\.\d+)'
    )

    url_data = defaultdict(list)
    total_requests = 0
    total_request_time = 0.0
    parsed_lines = 0
    failed_lines = 0

    try:
        with open_log_file(log_file_path) as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                match = log_pattern.match(line)
                if match:
                    data = match.groupdict()
                    request = data['request']
                    request_time = float(data['request_time'])

                    # Извлекаем URL из request (метод + URL)
                    url_match = re.match(r'(\S+)\s+(\S+)', request)
                    if url_match:
                        url = url_match.group(2)  # Берем только URL, без метода
                        url_data[url].append(request_time)
                        total_requests += 1
                        total_request_time += request_time
                        parsed_lines += 1
                    else:
                        print(f"Предупреждение: не удалось разобрать request в строке {line_num}: {request}")
                        failed_lines += 1
                else:
                    print(f"Предупреждение: не удалось разобрать строку {line_num}: {line[:100]}...")
                    failed_lines += 1

    except FileNotFoundError:
        print(f"Ошибка: файл {log_file_path} не найден")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        sys.exit(1)

    print(f"Успешно обработано строк: {parsed_lines}")
    if failed_lines > 0:
        print(f"Не удалось обработать строк: {failed_lines}")

    return url_data, total_requests, total_request_time


def calculate_statistics(url_data, total_requests, total_request_time):
    """
    Вычисляет статистику для каждого URL
    """
    statistics_data = []

    for url, times in url_data.items():
        count = len(times)
        count_perc = (count / total_requests) * 100 if total_requests > 0 else 0
        time_sum = sum(times)
        time_perc = (time_sum / total_request_time) * 100 if total_request_time > 0 else 0
        time_avg = statistics.mean(times) if times else 0
        time_max = max(times) if times else 0
        time_med = statistics.median(times) if times else 0

        statistics_data.append({
            'url': url,
            'count': count,
            'count_perc': count_perc,
            'time_sum': time_sum,
            'time_perc': time_perc,
            'time_avg': time_avg,
            'time_max': time_max,
            'time_med': time_med
        })

    # Сортируем по убыванию count
    statistics_data.sort(key=lambda x: x['count'], reverse=True)

    return statistics_data


def generate_html_table(statistics_data, output_file='log_analysis.html'):
    """
    Генерирует HTML таблицу с результатами
    """
    # Создаем строки таблицы
    table_rows = ""
    for data in statistics_data:
        table_rows += f"""
                <tr>
                    <td class="url" title="{data['url']}">{data['url']}</td>
                    <td class="number">{data['count']}</td>
                    <td class="number">{data['count_perc']:.2f}%</td>
                    <td class="number">{data['time_sum']:.3f}</td>
                    <td class="number">{data['time_perc']:.2f}%</td>
                    <td class="number">{data['time_avg']:.3f}</td>
                    <td class="number">{data['time_max']:.3f}</td>
                    <td class="number">{data['time_med']:.3f}</td>
                </tr>"""

    # HTML шаблон с использованием f-strings для избежания конфликта с фигурными скобками в CSS
    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Анализ логов Nginx</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            cursor: pointer;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .number {{
            text-align: right;
            font-family: monospace;
        }}
        .url {{
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .footer {{
            margin-top: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
        .warning {{
            color: #ff6b00;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Анализ логов Nginx</h1>
        <table id="logTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">URL</th>
                    <th onclick="sortTable(1)">Count</th>
                    <th onclick="sortTable(2)">Count %</th>
                    <th onclick="sortTable(3)">Time Sum</th>
                    <th onclick="sortTable(4)">Time %</th>
                    <th onclick="sortTable(5)">Time Avg</th>
                    <th onclick="sortTable(6)">Time Max</th>
                    <th onclick="sortTable(7)">Time Med</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        <div class="footer">
            Сгенерировано автоматически | Всего записей: {len(statistics_data)}
        </div>
    </div>

    <script>
        let currentSortColumn = -1;
        let currentSortDirection = 1;

        function sortTable(columnIndex) {{
            const table = document.getElementById("logTable");
            const tbody = table.getElementsByTagName("tbody")[0];
            const rows = Array.from(tbody.getElementsByTagName("tr"));

            const isNumeric = columnIndex > 0; // Все колонки кроме URL содержат числа

            // Если кликаем на ту же колонку, меняем направление сортировки
            if (currentSortColumn === columnIndex) {{
                currentSortDirection = -currentSortDirection;
            }} else {{
                currentSortColumn = columnIndex;
                currentSortDirection = 1;
            }}

            rows.sort((a, b) => {{
                let aValue = a.cells[columnIndex].textContent;
                let bValue = b.cells[columnIndex].textContent;

                if (isNumeric) {{
                    aValue = parseFloat(aValue) || 0;
                    bValue = parseFloat(bValue) || 0;
                    return (aValue - bValue) * currentSortDirection;
                }} else {{
                    return aValue.localeCompare(bValue) * currentSortDirection;
                }}
            }});

            // Очищаем и перезаполняем tbody
            while (tbody.firstChild) {{
                tbody.removeChild(tbody.firstChild);
            }}

            rows.forEach(row => tbody.appendChild(row));

            // Обновляем индикаторы сортировки в заголовках
            updateSortIndicators(columnIndex);
        }}

        function updateSortIndicators(activeColumn) {{
            const headers = document.querySelectorAll('th');
            headers.forEach((header, index) => {{
                header.textContent = header.textContent.replace(' ▲', '').replace(' ▼', '');
                if (index === activeColumn) {{
                    header.textContent += currentSortDirection === 1 ? ' ▲' : ' ▼';
                }}
            }});
        }}
    </script>
</body>
</html>"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML отчет сохранен в файл: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Анализ логов nginx и генерация HTML отчета')
    parser.add_argument('log_file', help='Путь к файлу логов nginx (поддерживает .gz файлы)')
    parser.add_argument('-o', '--output', default='log_analysis.html',
                        help='Имя выходного HTML файла (по умолчанию: log_analysis.html)')
    parser.add_argument('--top', type=int, default=0,
                        help='Показать только TOP N URL (по умолчанию: все)')

    args = parser.parse_args()

    if not os.path.exists(args.log_file):
        print(f"Ошибка: файл {args.log_file} не существует")
        sys.exit(1)

    print(f"Анализ файла: {args.log_file}")
    print("Определение типа файла...")

    file_type = detect_file_type(args.log_file)
    print(f"Тип файла: {'gzip (сжатый)' if file_type == 'gzip' else 'текстовый'}")

    print("Парсинг логов...")

    url_data, total_requests, total_request_time = parse_log_file(args.log_file)

    print(f"Найдено записей: {total_requests}")
    print(f"Уникальных URL: {len(url_data)}")
    print(f"Общее время запросов: {total_request_time:.3f} секунд")

    print("Вычисление статистики...")
    statistics_data = calculate_statistics(url_data, total_requests, total_request_time)

    if args.top > 0:
        statistics_data = statistics_data[:args.top]
        print(f"Ограничение вывода до {args.top} записей")

    print("Генерация HTML отчета...")
    generate_html_table(statistics_data, args.output)

    print("Готово!")


if __name__ == "__main__":
    main()
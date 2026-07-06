"""
Примеры использования EduBot

Демонстрирует различные сценарии работы с образовательным ботом.
"""
import asyncio
from orchestrator import AgentOrchestrator


async def example_1_auto_routing():
    """
    Пример 1: Автоматическая маршрутизация запросов
    
    Оркестратор автоматически определяет тип запроса
    и направляет его к подходящему агенту.
    """
    print("=" * 60)
    print("Пример 1: Автоматическая маршрутизация")
    print("=" * 60)
    
    orchestrator = AgentOrchestrator()
    orchestrator.initialize()
    
    # Запрос к учителю (автоматически)
    print("\n--- Запрос к учителю ---")
    response = await orchestrator.process_request(
        "Объясни, что такое словарь (dict) в Python"
    )
    print(f"Агент: {response.agent_name}")
    print(f"Ответ: {response.content[:200]}...")
    
    # Запрос к ревьюеру (автоматически)
    print("\n--- Запрос к ревьюеру ---")
    response = await orchestrator.process_request(
        "Проверь мой код: def add(a,b): return a+b"
    )
    print(f"Агент: {response.agent_name}")
    print(f"Ответ: {response.content[:200]}...")
    
    # Запрос к тестировщику (автоматически)
    print("\n--- Запрос к тестировщику ---")
    response = await orchestrator.process_request(
        "Напиши тесты для функции: def multiply(a, b): return a * b"
    )
    print(f"Агент: {response.agent_name}")
    print(f"Ответ: {response.content[:200]}...")


async def example_2_full_pipeline():
    """
    Пример 2: Полный пайплайн анализа кода
    
    Запускает все три агента последовательно:
    1. Учитель объясняет концепции
    2. Ревьюер проверяет код
    3. Тестировщик создает тесты
    """
    print("\n" + "=" * 60)
    print("Пример 2: Полный пайплайн анализа кода")
    print("=" * 60)
    
    orchestrator = AgentOrchestrator()
    orchestrator.initialize()
    
    code = """
def find_max(numbers):
    max_num = numbers[0]
    for num in numbers:
        if num > max_num:
            max_num = num
    return max_num
    """
    
    responses = await orchestrator.run_full_pipeline(code)
    
    for i, response in enumerate(responses, 1):
        print(f"\n--- Шаг {i}: {response.agent_name} ---")
        print(response.content[:300])


async def example_3_custom_chain():
    """
    Пример 3: Пользовательская цепочка агентов
    
    Вы можете определить свой порядок обработки.
    """
    print("\n" + "=" * 60)
    print("Пример 3: Пользовательская цепочка агентов")
    print("=" * 60)
    
    orchestrator = AgentOrchestrator()
    orchestrator.initialize()
    
    code = """
def reverse_string(text):
    result = ''
    for char in text:
        result = char + result
    return result
    """
    
    # Сначала ревью, потом тесты
    chain = ["code_reviewer", "tester"]
    responses = await orchestrator.run_custom_chain(code, chain)
    
    for response in responses:
        print(f"\n--- {response.agent_name} ---")
        print(response.content[:300])


async def example_4_classification():
    """
    Пример 4: Демонстрация классификации запросов
    """
    print("\n" + "=" * 60)
    print("Пример 4: Классификация запросов")
    print("=" * 60)
    
    orchestrator = AgentOrchestrator()
    
    test_requests = [
        "Что такое список в Python?",
        "Объясни декораторы",
        "Проверь мой код: print('hello')",
        "Напиши тесты для функции add",
        "def foo(): pass - ревью пожалуйста",
        "Как использовать list comprehension?",
        "test this function: def bar(x): return x"
    ]
    
    for request in test_requests:
        agent = orchestrator.classify_request(request)
        print(f"  {request[:40]:<40} -> {agent}")


async def example_5_teaching_scenario():
    """
    Пример 5: Сценарий обучения студента
    """
    print("\n" + "=" * 60)
    print("Пример 5: Сценарий обучения")
    print("=" * 60)
    
    orchestrator = AgentOrchestrator()
    orchestrator.initialize()
    
    # Студент изучает списки
    print("\n--- Урок 1: Списки ---")
    response = await orchestrator.process_request(
        "Привет! Я новичок в Python. Объясни, что такое списки"
    )
    print(response.content[:300])
    
    # Студент пишет код
    print("\n--- Урок 2: Проверка кода ---")
    response = await orchestrator.process_request(
        """
        Проверь мой код:
        ```python
        my_list = [1, 2, 3]
        for i in range(len(my_list)):
            print(my_list[i])
        ```
        """
    )
    print(response.content[:300])
    
    # Студент хочет тесты
    print("\n--- Урок 3: Тесты ---")
    response = await orchestrator.process_request(
        """
        Напиши тесты для:
        ```python
        def sum_list(lst):
            total = 0
            for item in lst:
                total += item
            return total
        ```
        """
    )
    print(response.content[:300])


async def main():
    """Запуск всех примеров"""
    print("\n🎓 EduBot - Примеры использования\n")
    
    # Пример 4 можно запустить без инициализации модели
    await example_4_classification()
    
    # Остальные примеры требуют загрузки модели
    # Раскомментируйте для запуска:
    
    # await example_1_auto_routing()
    # await example_2_full_pipeline()
    # await example_3_custom_chain()
    # await example_5_teaching_scenario()
    
    print("\n✅ Примеры завершены!")


if __name__ == "__main__":
    asyncio.run(main())

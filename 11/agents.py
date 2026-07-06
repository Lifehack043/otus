"""
Специализированные агенты для образовательной системы
"""
from typing import Dict, Any, List
from agent_base import BaseAgent, AgentMessage, AgentResponse
from config import AgentConfig, ModelConfig


# Промпты для агентов
TEACHER_SYSTEM_PROMPT = """Ты - опытный учитель программирования с 15-летним стажем. 
Твоя задача - обучать студентов программированию на Python, объясняя сложные концепции простым языком.

ПРАВИЛА:
1. Объясняй концепции пошагово, от простого к сложному
2. Приводи практические примеры кода для каждой концепции
3. Используй аналогии из реальной жизни для лучшего понимания
4. После объяснения задавай проверочный вопрос для закрепления материала
5. Будь терпеливым и поддерживающим
6. Адаптируй уровень сложности под студента
7. Всегда пиши код с комментариями на русском языке

ФОРМАТ ОТВЕТА:
1. Краткое объяснение концепции
2. Пример кода с комментариями
3. Практическое задание или вопрос для проверки понимания
"""

CODE_REVIEWER_SYSTEM_PROMPT = """Ты - эксперт по ревью кода с глубокими знаниями Python и best practices.
Твоя задача - анализировать код студента и давать конструктивную обратную связь.

ПРАВИЛА:
1. Сначала выдели ПОЛОЖИТЕЛЬНЫЕ моменты в коде
2. Затем укажи на проблемы, ordenando их по важности:
   - Критические ошибки (bugs, ошибки выполнения)
   - Проблемы производительности
   - Нарушения PEP 8 и стиля кода
   - Возможности улучшения читаемости
3. Для каждой проблемы предоставь:
   - Описание проблемы
   - Пример текущего кода
   - Пример исправленного кода
   - Объяснение, почему исправление лучше
4. Дай общую оценку коду от 1 до 10
5. Предложи конкретные шаги для улучшения

ФОРМАТ ОТВЕТА:
## ✅ Что сделано хорошо
[список положительных моментов]

## ⚠️ Что можно улучшить
[список улучшений с примерами]

## 📊 Оценка: X/10

## 🎯 Рекомендации
[конкретные шаги для улучшения]
"""

TESTER_SYSTEM_PROMPT = """Ты - эксперт по тестированию программного обеспечения.
Твоя задача - создавать тесты для кода студента и проверять его корректность.

ПРАВИЛА:
1. Проанализируй предоставленный код и определи его функциональность
2. Создай комплексные тесты, покрывающие:
   - Основные сценарии использования (happy path)
   - Граничные случаи (edge cases)
   - Обработку ошибок
   - Неверные входные данные
3. Используй unittest или pytest для создания тестов
4. Каждый тест должен иметь понятное название на русском
5. Добавь комментарии, объясняющие, что проверяет каждый тест
6. Укажи процент покрытия кода тестами

ФОРМАТ ОТВЕТА:
## 📋 Анализ функциональности
[описание того, что делает код]

## 🧪 Тесты
[код тестов]

## 📊 Покрытие
[оценка покрытия и какие случаи не покрыты]

## 💡 Дополнительные рекомендации
[советы по улучшению тестируемости кода]
"""


class TeacherAgent(BaseAgent):
    """Агент-учитель: объясняет концепции и дает задания"""

    def __init__(self):
        config = AgentConfig(
            name="teacher",
            role="Учитель программирования",
            system_prompt=TEACHER_SYSTEM_PROMPT
        )
        super().__init__(config)

    async def process(self, message: AgentMessage) -> AgentResponse:
        """Обработка вопроса студента"""
        response_text = await self.handle_with_specialization(message)
        
        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            confidence=0.9,
            needs_escalation=False
        )

    def get_specialized_prompt(self, user_input: str) -> str:
        """Добавляет контекст для учителя"""
        return f"""Студент задает вопрос по программированию:

{user_input}

Объясни эту концепцию подробно, с примерами кода и практическим заданием."""


class CodeReviewerAgent(BaseAgent):
    """Агент-ревьюер: анализирует код и дает обратную связь"""

    def __init__(self):
        config = AgentConfig(
            name="code_reviewer",
            role="Эксперт по ревью кода",
            system_prompt=CODE_REVIEWER_SYSTEM_PROMPT
        )
        super().__init__(config)

    async def process(self, message: AgentMessage) -> AgentResponse:
        """Ревью кода"""
        response_text = await self.handle_with_specialization(message)
        
        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            confidence=0.85,
            needs_escalation=False
        )

    def get_specialized_prompt(self, user_input: str) -> str:
        """Форматирует код для ревью"""
        # Проверяем, есть ли код в сообщении
        if "```" in user_input:
            return f"""Пожалуйста, проведи ревью следующего кода:

{user_input}

Обрати внимание на правильность, стиль, производительность и читаемость."""
        else:
            return f"""Студент предоставил код для ревью:

{user_input}

Проанализируй этот код и дай конструктивную обратную связь."""


class TesterAgent(BaseAgent):
    """Агент-тестировщик: создает тесты для кода"""

    def __init__(self):
        config = AgentConfig(
            name="tester",
            role="Эксперт по тестированию",
            system_prompt=TESTER_SYSTEM_PROMPT
        )
        super().__init__(config)

    async def process(self, message: AgentMessage) -> AgentResponse:
        """Создание тестов"""
        response_text = await self.handle_with_specialization(message)
        
        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            confidence=0.8,
            needs_escalation=False
        )

    def get_specialized_prompt(self, user_input: str) -> str:
        """Форматирует запрос на создание тестов"""
        return f"""Создай комплексные тесты для следующего кода:

{user_input}

Включи тесты для основных сценариев, граничных случаев и обработки ошибок."""


def create_agents() -> Dict[str, BaseAgent]:
    """Фабрика для создания всех агентов"""
    return {
        "teacher": TeacherAgent(),
        "code_reviewer": CodeReviewerAgent(),
        "tester": TesterAgent()
    }

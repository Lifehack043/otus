"""
Оркестратор - управляет цепочкой агентов и маршрутизацией сообщений
"""
import asyncio
import re
from typing import Dict, List, Optional, Tuple
from agent_base import BaseAgent, AgentMessage, AgentResponse
from agents import create_agents


class AgentOrchestrator:
    """
    Оркестратор управляет взаимодействием между агентами.
    Определяет, какой агент должен обработать запрос,
    и координирует цепочку обработки.
    """

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.initialized = False
        # Паттерны для классификации запросов
        self.patterns = {
            "code_review": [
                r"ревью", r"review", r"проверь код", r"посмотри код",
                r"что не так", r"ошибка в коде", r"улучши код",
                r"код плохо", r"как улучшить", r"кодирование"
            ],
            "testing": [
                r"тест", r"test", r"проверка", r"юнит-тест",
                r"unittest", r"pytest", r"напиши тест", r"тесты для"
            ],
            "teaching": [
                r"что такое", r"как работает", r"объясни", r"учи меня",
                r"помоги понять", r"что это", r"для чего", r"почему",
                r"как использовать", r"пример", r"tutorial"
            ]
        }

    def initialize(self):
        """Инициализация всех агентов"""
        if self.initialized:
            return

        # Создаем агентов
        self.agents = create_agents()

        # Общий LLM клиент для всех агентов (экономия ресурсов)
        from llm_client import HuggingFaceLLMClient
        from config import ModelConfig

        shared_client = HuggingFaceLLMClient(ModelConfig())

        # Инициализируем каждого агента
        for agent in self.agents.values():
            agent.initialize(shared_client)

        self.initialized = True
        print("Оркестратор инициализирован!")

    def classify_request(self, message: str) -> str:
        """
        Классифицирует запрос и определяет, какой агент должен его обработать.
        Возвращает имя агента.
        """
        message_lower = message.lower()

        scores = {
            "code_reviewer": 0,
            "tester": 0,
            "teacher": 0
        }

        # Проверяем паттерны
        for pattern in self.patterns["code_review"]:
            if re.search(pattern, message_lower):
                scores["code_reviewer"] += 2

        for pattern in self.patterns["testing"]:
            if re.search(pattern, message_lower):
                scores["tester"] += 2

        for pattern in self.patterns["teaching"]:
            if re.search(pattern, message_lower):
                scores["teacher"] += 1

        # Если есть код в сообщении, увеличиваем вес для ревьюера
        if "```" in message:
            scores["code_reviewer"] += 1

        # Выбираем агента с максимальным счетом
        best_agent = max(scores, key=scores.get)

        # Если все счета равны 0, по умолчанию учитель
        if scores[best_agent] == 0:
            return "teacher"

        return best_agent

    async def process_request(self, user_message: str, user_name: str = "student") -> AgentResponse:
        """
        Обрабатывает запрос пользователя, направляя его к подходящему агенту.
        """
        if not self.initialized:
            self.initialize()

        # Классифицируем запрос
        target_agent_name = self.classify_request(user_message)
        target_agent = self.agents[target_agent_name]

        print(f"\n📋 Запрос классифицирован как: {target_agent_name}")
        print(f"🤖 Обработка агентом: {target_agent}")

        # Создаем сообщение
        message = AgentMessage(
            sender=user_name,
            receiver=target_agent_name,
            content=user_message
        )

        # Обрабатываем запрос
        response = await target_agent.process(message)

        return response

    async def run_full_pipeline(self, user_message: str, user_name: str = "student") -> List[AgentResponse]:
        """
        Запускает полный пайплайн: учитель объясняет -> ревьюер проверяет код -> тестировщик создает тесты.
        Полезно когда пользователь предоставляет код и хочет полную обратную связь.
        """
        if not self.initialized:
            self.initialize()

        responses = []

        # Шаг 1: Учитель объясняет концепцию
        print("\n📚 Шаг 1: Учитель объясняет концепцию...")
        teacher_message = AgentMessage(
            sender=user_name,
            receiver="teacher",
            content=f"Объясни концепции, использованные в этом коде:\n\n{user_message}"
        )
        teacher_response = await self.agents["teacher"].process(teacher_message)
        responses.append(teacher_response)

        # Шаг 2: Ревьюер проверяет код
        print("\n🔍 Шаг 2: Ревьюер проверяет код...")
        reviewer_message = AgentMessage(
            sender="teacher",
            receiver="code_reviewer",
            content=user_message
        )
        reviewer_response = await self.agents["code_reviewer"].process(reviewer_message)
        responses.append(reviewer_response)

        # Шаг 3: Тестировщик создает тесты
        print("\n🧪 Шаг 3: Тестировщик создает тесты...")
        tester_message = AgentMessage(
            sender="code_reviewer",
            receiver="tester",
            content=user_message
        )
        tester_response = await self.agents["tester"].process(tester_message)
        responses.append(tester_response)

        return responses

    async def run_custom_chain(self, user_message: str, chain: List[str], user_name: str = "student") -> List[AgentResponse]:
        """
        Запускает пользовательскую цепочку агентов.
        chain - список имен агентов в порядке обработки.
        """
        if not self.initialized:
            self.initialize()

        responses = []
        previous_content = user_message

        for agent_name in chain:
            if agent_name not in self.agents:
                print(f"⚠️ Агент {agent_name} не найден, пропускаем...")
                continue

            print(f"\n🤖 Обработка агентом: {agent_name}")

            message = AgentMessage(
                sender=user_name if agent_name == chain[0] else chain[chain.index(agent_name) - 1],
                receiver=agent_name,
                content=previous_content
            )

            response = await self.agents[agent_name].process(message)
            responses.append(response)
            previous_content = response.content

        return responses

    def get_available_agents(self) -> List[str]:
        """Возвращает список доступных агентов"""
        return list(self.agents.keys())

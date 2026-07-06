"""
Базовый класс агента и абстракции для multi-agent системы
"""
import asyncio
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from config import AgentConfig, ModelConfig
from llm_client import HuggingFaceLLMClient, BaseLLMClient


@dataclass
class AgentMessage:
    """Сообщение между агентами"""
    sender: str
    receiver: str
    content: str
    message_type: str = "text"  # text, code, feedback, question
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        return cls(
            sender=data["sender"],
            receiver=data["receiver"],
            content=data["content"],
            message_type=data.get("message_type", "text"),
            metadata=data.get("metadata", {})
        )


@dataclass
class AgentResponse:
    """Ответ агента"""
    agent_name: str
    content: str
    confidence: float = 1.0  # Уверенность агента в ответе
    needs_escalation: bool = False  # Нужна ли передача другому агенту
    suggested_next_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Базовый класс для всех агентов"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self.role = config.role
        self.system_prompt = config.system_prompt
        self.llm_client: Optional[BaseLLMClient] = None
        self.context: List[Dict[str, str]] = []  # Контекст разговора
        self.max_context_size: int = 20

    def initialize(self, shared_llm_client: Optional[BaseLLMClient] = None):
        """Инициализация агента с LLM клиентом"""
        if shared_llm_client:
            self.llm_client = shared_llm_client
        else:
            self.llm_client = HuggingFaceLLMClient(self.config.model_config)

    @abstractmethod
    async def process(self, message: AgentMessage) -> AgentResponse:
        """Обработка входящего сообщения"""
        pass

    async def _generate_response(self, user_prompt: str) -> str:
        """Генерация ответа с помощью LLM"""
        if not self.llm_client:
            raise RuntimeError("Агент не инициализирован. Вызовите initialize()")

        response = await self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=self.system_prompt
        )
        return response

    def _update_context(self, role: str, content: str):
        """Обновление контекста разговора"""
        self.context.append({"role": role, "content": content})
        if len(self.context) > self.max_context_size:
            self.context = self.context[-self.max_context_size:]

    def get_specialized_prompt(self, user_input: str) -> str:
        """
        Переопределите в подклассах для специфической обработки промпта
        """
        return user_input

    async def handle_with_specialization(self, message: AgentMessage) -> str:
        """Обработка сообщения со специализированным промптом"""
        specialized_prompt = self.get_specialized_prompt(message.content)
        self._update_context("user", specialized_prompt)
        response = await self._generate_response(specialized_prompt)
        self._update_context("assistant", response)
        return response

    def reset_context(self):
        """Сброс контекста"""
        self.context = []

    def __repr__(self):
        return f"<Agent: {self.name}, Role: {self.role}>"

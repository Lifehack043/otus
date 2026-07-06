"""
Базовый LLM клиент для работы с моделями HuggingFace
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM
from config import ModelConfig
import torch


class BaseLLMClient(ABC):
    """Абстрактный базовый класс для LLM клиентов"""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Генерация ответа на основе промпта"""
        pass

    @abstractmethod
    async def generate_chat(self, messages: List[Dict[str, str]]) -> str:
        """Генерация ответа на основе истории чата"""
        pass


class HuggingFaceLLMClient(BaseLLMClient):
    """Клиент для работы с моделями HuggingFace"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.tokenizer = None
        self.model = None
        self._loaded = False

    def load_model(self):
        """Загрузка модели и токенизатора"""
        if self._loaded:
            return

        print(f"Загрузка модели {self.config.model_name}...")

        # Загрузка токенизатора
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            trust_remote_code=True
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Загрузка модели
        model_kwargs = {
            "trust_remote_code": True,
            "device_map": "auto" if self.config.use_gpu else "cpu",
        }

        if self.config.load_in_4bit:
            try:
                from transformers import BitsAndBytesConfig
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16 if self.config.use_gpu else torch.float32
                )
                model_kwargs["quantization_config"] = bnb_config
            except ImportError:
                print("Warning: bitsandbytes not available, loading without quantization")

        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.model_name,
            **model_kwargs
        )

        self._loaded = True
        print("Модель загружена!")

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Генерация ответа на основе промпта"""
        self.load_model()

        # Формируем сообщения для chat-модели
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return await self.generate_chat(messages)

    async def generate_chat(self, messages: List[Dict[str, str]]) -> str:
        """Генерация ответа на основе истории чата"""
        self.load_model()

        # Применяем chat template
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # Токенизация
        inputs = self.tokenizer([text], return_tensors="pt")

        if self.config.use_gpu:
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        # Генерация
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.config.max_new_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                repetition_penalty=self.config.repetition_penalty,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        # Декодирование ответа
        generated_tokens = outputs[0][inputs['input_ids'].shape[1]:]
        response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)

        return response.strip()

    def __del__(self):
        """Освобождение ресурсов"""
        if self.model is not None:
            del self.model
        if self.tokenizer is not None:
            del self.tokenizer

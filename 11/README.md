# 🎓 EduBot - Образовательный Multi-Agent AI Ассистент

Интеллектуальная система для обучения программированию на Python, построенная на основе открытых моделей HuggingFace с использованием multi-agent архитектуры.

## 📋 Описание проекта

EduBot - это цепь специализированных AI-агентов, каждый из которых отвечает за свою область:

- **📚 Teacher (Учитель)** - Объясняет концепции программирования, дает примеры и задания
- **🔍 Code Reviewer (Ревьюер)** - Анализирует код, дает конструктивную обратную связь
- **🧪 Tester (Тестировщик)** - Создает комплексные тесты для вашего кода

Система автоматически определяет тип запроса и направляет его к подходящему агенту, а также поддерживает запуск цепочек агентов для комплексного анализа.

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Пользователь (CLI)                    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   AgentOrchestrator                      │
│  - Классификация запросов                               │
│  - Маршрутизация к агентам                              │
│  - Управление цепочками агентов                         │
└──────────┬──────────────────┬──────────────────┬────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   TeacherAgent   │ │ CodeReviewerAgent│ │   TesterAgent    │
│                  │ │                  │ │                  │
│ • Объяснения     │ │ • Ревью кода     │ │ • Создание тестов│
│ • Примеры        │ │ • Оценка         │ │ • Покрытие       │
│ • Задания        │ │ • Рекомендации   │ │ • Рекомендации   │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              HuggingFaceLLMClient                        │
│                                                         │
│  Модель: Qwen/Qwen2.5-3B-Instruct                       │
│  Квантование: 4-bit (bitsandbytes)                      │
│  PEFT/LoRA: Поддержка дообучения                        │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Запуск CLI интерфейса

```bash
python cli.py
```

### 3. Использование

```
> Что такое декораторы в Python?
[Автоматически направляется к TeacherAgent]

> Проверь мой код:
> def hello(name):
>     print('hello ' + name)
[Автоматически направляется к CodeReviewerAgent]

> Напиши тесты для функции add(a, b)
[Автоматически направляется к TesterAgent]
```

## 📖 Документация по API

### AgentOrchestrator

Основной класс для управления агентами:

```python
from orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()
orchestrator.initialize()

# Автоматическая маршрутизация
response = await orchestrator.process_request("Что такое список в Python?")

# Полный пайплайн (учитель -> ревьюер -> тестировщик)
responses = await orchestrator.run_full_pipeline("def my_func(): ...")

# Пользовательская цепочка
responses = await orchestrator.run_custom_chain(
    "def my_func(): ...",
    chain=["teacher", "code_reviewer", "tester"]
)
```

### Создание кастомного агента

```python
from agent_base import BaseAgent, AgentMessage, AgentResponse
from config import AgentConfig

class MyCustomAgent(BaseAgent):
    def __init__(self):
        config = AgentConfig(
            name="my_agent",
            role="Мой агент",
            system_prompt="Ты - ..."
        )
        super().__init__(config)
    
    async def process(self, message: AgentMessage) -> AgentResponse:
        response = await self.handle_with_specialization(message)
        return AgentResponse(
            agent_name=self.name,
            content=response,
            confidence=0.9
        )
```

## 🎓 Fine-Tuning модели

### Запуск обучения

```bash
python fine_tuning.py
```

### Конфигурация обучения

В [`config.py`](config.py) можно настроить:

```python
TrainingConfig(
    learning_rate=2e-4,
    num_train_epochs=3,
    lora_r=16,
    lora_alpha=32,
    max_seq_length=2048,
    # ...
)
```

### Объединение весов LoRA

```python
from fine_tuning import merge_and_save

merge_and_save(
    model_path="./fine_tuned_model",
    output_path="./merged_model"
)
```

## 📁 Структура проекта

```
.
├── README.md           # Эта документация
├── requirements.txt    # Зависимости
├── config.py           # Конфигурация модели и обучения
├── llm_client.py       # LLM клиент для HuggingFace
├── agent_base.py       # Базовый класс агента
├── agents.py           # Специализированные агенты
├── orchestrator.py     # Оркестратор агентов
├── cli.py              # CLI интерфейс
└── fine_tuning.py      # Скрипт для fine-tuning
```

## 🎯 Примеры использования

### Пример 1: Вопрос к учителю

```
> Объясни, что такое генераторы в Python

📋 Запрос классифицирован как: teacher
🤖 Обработка агентом: <Agent: teacher, Role: Учитель программирования>

Генераторы в Python - это специальные функции, которые возвращают 
итератор...
```

### Пример 2: Ревью кода

```
> Проверь мой код:
> ```python
> def get_user_name(user_id):
>     users = load_all_users()
>     for u in users:
>         if u.id == user_id:
>             return u.name
> ```

📋 Запрос классифицирован как: code_reviewer
🤖 Обработка агентом: <Agent: code_reviewer, Role: Эксперт по ревью кода>

## ✅ Что сделано хорошо
- Понятное имя функции
...
```

### Пример 3: Полный пайплайн

```
> /pipeline
⚠️ Введите код для полной проверки:
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)

📚 Шаг 1: Учитель объясняет концепцию...
🔍 Шаг 2: Ревьюер проверяет код...
🧪 Шаг 3: Тестировщик создает тесты...
```

## ⚙️ Требования к системе

- Python 3.9+
- GPU с 4GB+ VRAM (для 4-bit квантования)
- 8GB+ RAM
- 10GB+ свободного места на диске (для модели)

## 📚 Используемые технологии

- **Qwen2.5-3B-Instruct** - Базовая LLM модель от Alibaba
- **PEFT/LoRA** - Эффективное дообучение
- **bitsandbytes** - 4-bit квантование
- **TRL** - Transformer Reinforcement Learning
- **HuggingFace Transformers** - Фреймворк для работы с моделями

## 📝 Лицензия

MIT License

## 👨‍💻 Автор

Проект создан для образовательных целей.

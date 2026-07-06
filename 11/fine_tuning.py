"""
Скрипт для fine-tuning модели Qwen2.5-3B-Instruct на образовательных данных
Использует LoRA (PEFT) для эффективной дообучения
"""
import os
import json
import torch
from datasets import load_dataset, Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    BitsAndBytesConfig,
    DataCollatorForSeq2Seq
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType
)
from trl import SFTTrainer
from config import TrainingConfig, ModelConfig


def prepare_educational_dataset() -> dict:
    """
    Подготавливает датасет для образовательного бота.
    Создает примеры в формате chat для SFT (Supervised Fine-Tuning).
    """
    
    # Примеры образовательных диалогов
    educational_examples = [
        {
            "conversations": [
                {"role": "system", "content": "Ты - опытный учитель программирования."},
                {"role": "user", "content": "Что такое список в Python и как его создать?"},
                {"role": "assistant", "content": "Список (list) в Python - это упорядоченная коллекция элементов, которая может содержать объекты разных типов.\n\nСоздание списка:\n```python\n# Пустой список\nempty_list = []\n\n# Список с элементами\nfruits = [\"яблоко\", \"банан\", \"апельсин\"]\nnumbers = [1, 2, 3, 4, 5]\nmixed = [1, \"текст\", 3.14, True]\n\n# Список с помощью list()\ndoubles = list(range(10))  # [0, 1, 2, ..., 9]\n```\n\nОсновные операции:\n- Добавление: `fruits.append(\"груша\")`\n- Доступ по индексу: `fruits[0]` → \"яблоко\"\n- Срезы: `fruits[1:3]` → [\"банан\", \"апельсин\"]\n- Длина: `len(fruits)` → 3\n\nПопробуйте создать список ваших любимых фильмов и вывести первый элемент!"}
            ]
        },
        {
            "conversations": [
                {"role": "system", "content": "Ты - эксперт по ревью кода."},
                {"role": "user", "content": "Проверь мой код:\ndef greet(name):\n    print('hello ' + name)"},
                {"role": "assistant", "content": "## ✅ Что сделано хорошо\n- Функция имеет понятное имя\n- Есть параметр для персонализации\n\n## ⚠️ Что можно улучшить\n1. Использовать f-strings вместо конкатенации:\n   ```python\n   # Было\n   print('hello ' + name)\n   # Стало\n   print(f'hello {name}')\n   ```\n2. Добавить docstring:\n   ```python\n   def greet(name: str) -> None:\n       \"\"\"Выводит приветственное сообщение.\"\"\"\n       print(f'hello {name}')\n   ```\n3. Добавить обработку пустого имени\n\n## 📊 Оценка: 6/10\n\n## 🎯 Рекомендации\n- Изучите PEP 8 для стиля кода\n- Используйте type hints\n- Добавляйте docstrings"}
            ]
        },
        {
            "conversations": [
                {"role": "system", "content": "Ты - эксперт по тестированию."},
                {"role": "user", "content": "Напиши тесты для функции:\ndef add(a, b):\n    return a + b"},
                {"role": "assistant", "content": "## 📋 Анализ функциональности\nФункция `add` принимает два параметра и возвращает их сумму.\n\n## 🧪 Тесты\n```python\nimport unittest\n\nclass TestAddFunction(unittest.TestCase):\n    \"\"\"Тесты для функции сложения.\"\"\"\n    \n    def test_add_positive_numbers(self):\n        \"\"\"Тест сложения положительных чисел.\"\"\"\n        self.assertEqual(add(2, 3), 5)\n    \n    def test_add_negative_numbers(self):\n        \"\"\"Тест сложения отрицательных чисел.\"\"\"\n        self.assertEqual(add(-1, -1), -2)\n    \n    def test_add_zero(self):\n        \"\"\"Тест сложения с нулем.\"\"\"\n        self.assertEqual(add(5, 0), 5)\n    \n    def test_add_floats(self):\n        \"\"\"Тест сложения дробных чисел.\"\"\"\n        self.assertAlmostEqual(add(0.1, 0.2), 0.3, places=7)\n    \n    def test_add_strings(self):\n        \"\"\"Тест конкатенации строк.\"\"\"\n        self.assertEqual(add(\"hello\", \" world\"), \"hello world\")\n\nif __name__ == \"__main__\":\n    unittest.main()\n```\n\n## 📊 Покрытие: ~80%\nНе покрыты: тесты с None, тесты с разными типами данных\n\n## 💡 Рекомендации\n- Добавьте валидацию типов входных данных"}
            ]
        },
        {
            "conversations": [
                {"role": "system", "content": "Ты - опытный учитель программирования."},
                {"role": "user", "content": "Объясни, что такое декораторы в Python"},
                {"role": "assistant", "content": "Декораторы в Python - это мощный инструмент, который позволяет изменять поведение функции или метода, не изменяя их код.\n\nПростая аналогия: декоратор как упаковка подарка - вы не меняете сам подарок, но добавляете красивую обертку.\n\nПример:\n```python\nimport time\nfrom functools import wraps\n\ndef timer(func):\n    \"\"\"Декоратор для измерения времени выполнения.\"\"\"\n    @wraps(func)\n    def wrapper(*args, **kwargs):\n        start = time.time()\n        result = func(*args, **kwargs)\n        end = time.time()\n        print(f\"{func.__name__} выполнилась за {end - start:.4f} сек\")\n        return result\n    return wrapper\n\n@timer\ndef slow_function():\n    \"\"\"Функция с задержкой.\"\"\"\n    time.sleep(1)\n\nslow_function()  # slow_function выполнилась за 1.0012 сек\n```\n\nПопробуйте создать декоратор, который логирует вызовы функции!"}
            ]
        },
        {
            "conversations": [
                {"role": "system", "content": "Ты - опытный учитель программирования."},
                {"role": "user", "content": "В чем разница между == и is в Python?"},
                {"role": "assistant", "content": "Отличный вопрос! Это частая причина путаницы.\n\n- `==` проверяет РАВЕНСТВО ЗНАЧЕНИЙ\n- `is` проверяет ИДЕНТИЧНОСТЬ (одинаковый объект в памяти)\n\nПример:\n```python\na = [1, 2, 3]\nb = [1, 2, 3]\nc = a\n\nprint(a == b)  # True - значения одинаковые\nprint(a is b)  # False - разные объекты в памяти\nprint(a is c)  # True - c ссылается на тот же объект, что и a\n```\n\nАналогия: Две одинаковые книги из магазина:\n- `==` - содержание книг одинаковое\n- `is` - это физически одна и та же книга?\n\nИспользуйте `==` для сравнения значений и `is` только для проверки на `None`!"}
            ]
        }
    ]
    
    # Создаем датасет
    dataset = Dataset.from_list(educational_examples)
    
    return {
        "train": dataset,
        "config": {
            "chat_template": "{% for message in conversations %}{% if message['role'] == 'user' %}{{ 'User: ' + message['content'] + '\\n' }}{% elif message['role'] == 'assistant' %}{{ 'Assistant: ' + message['content'] + '\\n\\n' }}{% endif %}{% endfor %}"
        }
    }


def load_external_dataset(config: TrainingConfig) -> Dataset:
    """
    Загружает внешний датасет для дообучения.
    """
    try:
        dataset = load_dataset(config.dataset_name, split=config.dataset_split)
        if config.max_samples:
            dataset = dataset.select(range(min(config.max_samples, len(dataset))))
        return dataset
    except Exception as e:
        print(f"Ошибка загрузки датасета: {e}")
        print("Используем локальный образовательный датасет...")
        return prepare_educational_dataset()["train"]


def train_model(config: TrainingConfig | None = None):
    """
    Основная функция для fine-tuning модели.
    """
    if config is None:
        config = TrainingConfig()
    
    model_config = ModelConfig()
    
    print("=" * 60)
    print("🚀 Начало fine-tuning модели")
    print("=" * 60)
    
    # 1. Загрузка токенизатора
    print("\n📦 Загрузка токенизатора...")
    tokenizer = AutoTokenizer.from_pretrained(
        model_config.model_name,
        trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # 2. Загрузка модели
    print("\n📦 Загрузка модели...")
    if model_config.load_in_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_config.model_name,
            quantization_config=bnb_config,
            trust_remote_code=True,
            device_map="auto"
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_config.model_name,
            trust_remote_code=True,
            device_map="auto"
        )
    
    # 3. Подготовка модели для k-bit training
    model = prepare_model_for_kbit_training(model)
    
    # 4. Настройка LoRA
    print("\n🔧 Настройка LoRA...")
    peft_config = LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=config.target_modules,
        task_type=TaskType.CAUSAL_LM,
        bias="none"
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    # 5. Загрузка данных
    print("\n📚 Загрузка данных...")
    dataset = prepare_educational_dataset()["train"]
    print(f"Загружено {len(dataset)} примеров")
    
    # 6. Настройка тренера
    print("\n⚙️ Настройка тренера...")
    training_args = TrainingArguments(
        output_dir=config.output_dir,
        num_train_epochs=config.num_train_epochs,
        per_device_train_batch_size=config.per_device_train_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        fp16=True,
        logging_steps=config.logging_steps,
        save_steps=config.save_steps,
        evaluation_strategy="no",
        report_to="none",
        warmup_ratio=config.warmup_ratio,
        weight_decay=config.weight_decay,
        max_seq_length=config.max_seq_length
    )
    
    # 7. Создание тренера
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        dataset_text_field="conversations",
        max_seq_length=config.max_seq_length,
        tokenizer=tokenizer,
        args=training_args,
        packing=False
    )
    
    # 8. Обучение
    print("\n🎓 Начало обучения...")
    trainer.train()
    
    # 9. Сохранение
    print(f"\n💾 Сохранение модели в {config.output_dir}...")
    model.save_pretrained(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)
    
    print("\n✅ Fine-tuning завершен!")
    print(f"Модель сохранена в: {config.output_dir}")
    
    return model, tokenizer


def merge_and_save(model_path: str = "./fine_tuned_model", output_path: str = "./merged_model"):
    """
    Объединяет LoRA веса с базовой моделью для деплоя.
    """
    from peft import PeftModel
    
    print("\n🔀 Объединение весов LoRA с базовой моделью...")
    
    # Загрузка базовой модели
    base_model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-3B-Instruct",
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    # Загрузка LoRA адаптера
    model = PeftModel.from_pretrained(base_model, model_path)
    model.merge_and_unload()
    
    # Сохранение
    model.save_pretrained(output_path)
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.save_pretrained(output_path)
    
    print(f"✅ Объединенная модель сохранена в: {output_path}")


if __name__ == "__main__":
    # Запуск обучения
    train_model()
    
    # Для объединения весов раскомментируйте:
    # merge_and_save()

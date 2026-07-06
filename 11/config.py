"""
Конфигурация проекта - образовательный multi-agent бот
"""
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ModelConfig:
    """Конфигурация базовой модели"""
    model_name: str = "Qwen/Qwen2.5-3B-Instruct"
    max_new_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    use_gpu: bool = True
    load_in_4bit: bool = True  # Квантование для экономии памяти

@dataclass
class AgentConfig:
    """Конфигурация агента"""
    name: str
    role: str
    system_prompt: str
    model_config: Optional[ModelConfig] = None

    def __post_init__(self):
        if self.model_config is None:
            self.model_config = ModelConfig()

@dataclass
class TrainingConfig:
    """Конфигурация для fine-tuning"""
    # Данные
    dataset_name: str = "HuggingFaceH4/ultrachat_200k"
    dataset_split: str = "train_sft"
    max_samples: int = 1000

    # Обучение
    learning_rate: float = 2e-4
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 4
    max_seq_length: int = 2048
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01

    # PEFT/LoRA
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    target_modules: list = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])

    # Сохранение
    output_dir: str = "./fine_tuned_model"
    save_steps: int = 100
    logging_steps: int = 10

"""
CLI интерфейс для взаимодействия с образовательным ботом
"""
import asyncio
import sys
from orchestrator import AgentOrchestrator


class CLIInterface:
    """Командный интерфейс для взаимодействия с ботом"""

    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.running = False

    def print_welcome(self):
        """Выводит приветственное сообщение"""
        print("=" * 60)
        print("🎓 Добро пожаловать в EduBot - Образовательный AI Ассистент!")
        print("=" * 60)
        print("\nДоступные агенты:")
        print("  📚 teacher - Объясняет концепции программирования")
        print("  🔍 code_reviewer - Проверяет ваш код")
        print("  🧪 tester - Создает тесты для вашего кода")
        print("\nКоманды:")
        print("  /help - Показать помощь")
        print("  /agents - Список агентов")
        print("  /pipeline - Запустить полный пайплайн (для кода)")
        print("  /chain <агенты> - Запустить цепочку агентов (через запятую)")
        print("  /quit или /exit - Выйти")
        print("  /reset - Сбросить контекст")
        print("\nПримеры:")
        print("  /chain teacher,code_reviewer,tester")
        print("  /pipeline")
        print("\nПросто введите ваш вопрос или код, и бот автоматически")
        print("выберет подходящего агента для ответа.")
        print("=" * 60)

    def print_help(self):
        """Выводит справку"""
        print("\n📖 Справка:")
        print("  - Просто введите вопрос, и бот выберет агента автоматически")
        print("  - Используйте /pipeline для полной проверки кода")
        print("  - Используйте /chain для ручной цепочки агентов")
        print("  - Для кода используйте блоки ```python ... ```")
        print()

    async def process_command(self, command: str) -> bool:
        """
        Обрабатывает команду. Возвращает False, если нужно выйти.
        """
        # Команды
        if command in ["/quit", "/exit"]:
            print("\n👋 До свидания! Удачи в изучении программирования!")
            return False

        if command == "/help":
            self.print_help()
            return True

        if command == "/agents":
            print("\n🤖 Доступные агенты:")
            for agent_name in self.orchestrator.get_available_agents():
                print(f"  - {agent_name}")
            return True

        if command == "/reset":
            for agent in self.orchestrator.agents.values():
                agent.reset_context()
            print("\n🔄 Контекст сброшен!")
            return True

        if command == "/pipeline":
            print("\n⚠️ Введите код для полной проверки (завершите пустой строкой):")
            code_lines = []
            while True:
                line = input()
                if line == "":
                    break
                code_lines.append(line)
            
            if code_lines:
                code = "\n".join(code_lines)
                await self.run_pipeline(code)
            else:
                print("Код пуст!")
            return True

        if command.startswith("/chain "):
            agents_str = command[7:].strip()
            chain = [a.strip() for a in agents_str.split(",")]
            
            print("\n⚠️ Введите ваш вопрос или код:")
            user_input = input("> ")
            await self.run_custom_chain(user_input, chain)
            return True

        # Обычный запрос
        await self.process_request(command)
        return True

    async def process_request(self, message: str):
        """Обрабатывает обычный запрос"""
        try:
            response = await self.orchestrator.process_request(message)
            print(f"\n{response.content}")
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")

    async def run_pipeline(self, code: str):
        """Запускает полный пайплайн"""
        try:
            responses = await self.orchestrator.run_full_pipeline(code)
            
            for i, response in enumerate(responses, 1):
                print(f"\n{'=' * 60}")
                print(f"📋 Ответ от {response.agent_name}:")
                print('=' * 60)
                print(response.content)
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")

    async def run_custom_chain(self, message: str, chain: list):
        """Запускает пользовательскую цепочку"""
        try:
            responses = await self.orchestrator.run_custom_chain(message, chain)
            
            for i, response in enumerate(responses, 1):
                print(f"\n{'=' * 60}")
                print(f"📋 Ответ от {response.agent_name}:")
                print('=' * 60)
                print(response.content)
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")

    async def run(self):
        """Запускает CLI интерфейс"""
        self.print_welcome()
        self.running = True

        print("\n💬 Введите ваш вопрос или команду:")

        while self.running:
            try:
                user_input = input("\n> ").strip()
                if not user_input:
                    continue
                
                self.running = await self.process_command(user_input)
            except EOFError:
                print("\n👋 До свидания!")
                break
            except KeyboardInterrupt:
                print("\n👋 До свидания!")
                break


async def main():
    """Точка входа"""
    cli = CLIInterface()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())

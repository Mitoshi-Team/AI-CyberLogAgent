#!/usr/bin/env python3
r"""CLI for AI Agent v2 log analysis.

Usage:
    cd C:\Users\litsu\PycharmProjects\AI-CyberLogAgent
    uv run -m log_ai_agent.ai_agent_v2.run

Or with options:
    uv run -m log_ai_agent.ai_agent_v2.run --help
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from log_ai_agent.ai_agent_v2.callbacks import get_callback_config
from log_ai_agent.ai_agent_v2.config import AgentConfig
from log_ai_agent.ai_agent_v2.pipeline.full_pipeline import create_pipeline

# =============================================================================
# Colors for terminal output
# =============================================================================


class Colors:
    """ANSI color codes."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_header(text: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}\n")


def print_stage(num: int, total: int, text: str):
    """Print stage indicator."""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}[Этап {num}/{total}] {text}{Colors.RESET}")


def print_separator():
    """Print separator line."""
    print(f"{Colors.BLUE}{'─' * 60}{Colors.RESET}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


# =============================================================================
# Log input
# =============================================================================


def get_log_input() -> str:
    """Get log content from user."""
    print_header("Ввод логов")

    print("Выберите способ ввода:")
    print("1. Загрузить из файла")
    print("2. Ввести текст вручную")
    print("3. Использовать тестовые логи")

    choice = input(f"\n{Colors.CYAN}Ваш выбор (1/2/3): {Colors.RESET}").strip()

    if choice == "1":
        file_path = input(f"{Colors.CYAN}Путь к файлу: {Colors.RESET}").strip()
        try:
            path = Path(file_path)
            content = path.read_text(encoding="utf-8")
            print_success(f"Файл загружен: {len(content)} байт")
            return content
        except Exception as e:
            print_error(f"Ошибка: {e}")
            return get_sample_logs()

    elif choice == "2":
        print("\nВведите текст (пустая строка для завершения):")
        lines = []
        while True:
            line = input()
            if not line.strip():
                break
            lines.append(line)
        content = "\n".join(lines)
        print_success(f"Введено {len(content)} байт")
        return content

    else:
        return get_sample_logs()


def get_sample_logs() -> str:
    """Use sample log content."""
    sample = """2026-03-21 10:15:23 INFO Application started
2026-03-21 10:15:45 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:46 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:47 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:48 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:49 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:16:00 ERROR SQL syntax error near 'SELECT * FROM users WHERE id=1 OR 1=1--'
2026-03-21 10:16:01 CRITICAL Database connection pool exhausted
2026-03-21 10:16:15 WARNING Suspicious file access: /etc/passwd
2026-03-21 10:16:30 ERROR Unauthorized API request from 10.0.0.55"""

    print_success("Используем тестовые логи")
    return sample


# =============================================================================
# Output formatting
# =============================================================================


def print_results(results: dict):
    """Print pipeline results."""
    print_header("Результаты анализа")

    if not results.get("success"):
        print_error(f"Анализ не удался: {results.get('error', 'Unknown error')}")
        return

    # Agent 1 results
    print_stage(2, 4, "Первичный анализ (Агент 1)")
    print_separator()
    if "agent1" in results.get("stages", {}):
        agent1 = results["stages"]["agent1"]
        print_success(f"Найдено событий: {agent1.get('events_found', 0)}")
        print(f"\n{Colors.CYAN}{agent1.get('primary_analysis', '')}{Colors.RESET}")
    else:
        print_warning("Нет результатов от Агента 1")

    # RAG results
    print_stage(3, 4, "Поиск MITRE (RAG)")
    print_separator()
    if "rag" in results.get("stages", {}):
        rag = results["stages"]["rag"]
        if rag.get("success"):
            print_success(f"Найдено техник: {rag.get('techniques_count', 0)}")
            print(f"{Colors.CYAN}{rag.get('mitre_context', '')}{Colors.RESET}")
        else:
            print_warning("RAG недоступен")
    else:
        print_warning("RAG отключен")

    # Agent 2 results
    print_stage(4, 4, "Финальный отчёт (Агент 2)")
    print_separator()
    if "agent2" in results.get("stages", {}):
        agent2 = results["stages"]["agent2"]

        severity_names = {1: "Критический", 2: "Высокий", 3: "Средний", 4: "Низкий"}
        threat_names = {
            1: "Вторжение",
            2: "Malware",
            3: "DDoS",
            4: "Утечка",
            5: "Доступ",
            6: "Фишинг",
            7: "SQL",
            8: "XSS",
            9: "Брутфорс",
            10: "Сканирование",
            11: "Другое",
        }

        severity = agent2.get("severity_level_id", 3)
        threat = agent2.get("threat_type_id", 11)

        severity_color = (
            Colors.RED
            if severity == 1
            else (Colors.YELLOW if severity == 2 else Colors.GREEN)
        )

        print(
            f"Уровень серьезности: {severity_color}{severity}/4 ({severity_names.get(severity, 'N/A')}){Colors.RESET}"
        )
        print(
            f"Тип угрозы: {Colors.YELLOW}{threat}/11 ({threat_names.get(threat, 'N/A')}){Colors.RESET}"
        )

        if agent2.get("mitre_techniques"):
            print(
                f"MITRE техники: {Colors.CYAN}{', '.join(agent2['mitre_techniques'])}{Colors.RESET}"
            )

        print_separator()
        print(f"{Colors.CYAN}{agent2.get('final_report', '')}{Colors.RESET}")
    else:
        print_warning("Нет результатов от Агента 2")

    # Summary
    print_header("Итоги")
    print(f"Размер логов: {results.get('log_size', 0)} байт")
    print(
        f"Время анализа: {Colors.YELLOW}{results.get('total_time_sec', 0):.1f} сек{Colors.RESET}"
    )


# =============================================================================
# Main
# =============================================================================


async def main():
    """Main entry point."""
    print_header("AI Agent v2 - Анализ логов")

    # Configuration
    print("Настройки:")
    use_rag_input = (
        input(f"{Colors.CYAN}Использовать RAG? (y/n, по умолчанию y): {Colors.RESET}")
        .strip()
        .lower()
    )
    use_rag = use_rag_input != "n"

    # Get log input
    log_content = get_log_input()
    print_separator()

    # Initialize pipeline
    print_stage(1, 4, "Инициализация пайплайна")

    try:
        config = AgentConfig.from_env()
        config.use_rag = use_rag

        print(f"ChromaDB path: {config.chroma_path}")
        print(f"Embedding model: {config.embedding_model}")
        print(f"RAG enabled: {use_rag}")

        # Create pipeline
        print("\nСоздание пайплайна...")
        pipeline = await create_pipeline(
            chroma_path=config.chroma_path,
            use_rag=config.use_rag,
            llm_config={
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            },
        )

        print_success("Пайплайн создан")

        # Run analysis
        print_separator()
        print("\nЗапуск анализа...")

        callback_config = get_callback_config(show_output=False)
        results = await pipeline.analyze(log_content, config=callback_config)

        # Print results
        print_results(results)

        print_header("Анализ завершён")

    except Exception as e:
        print_error(f"Ошибка: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Прервано пользователем{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Ошибка: {e}{Colors.RESET}")
        sys.exit(1)

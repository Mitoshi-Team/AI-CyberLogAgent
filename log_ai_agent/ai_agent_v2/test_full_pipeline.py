#!/usr/bin/env python3
r"""
Autonomous test script for AI Agent v2 full pipeline.

Features:
- Initializes ChromaDB with MITRE ATT&CK knowledge base
- Interactive log input (file or manual entry)
- Step-by-step pipeline execution with detailed output
- Completely isolated from main application

Usage:
    cd C:\Users\litsu\PycharmProjects\AI-CyberLogAgent
    uv run -m log_ai_agent.ai_agent_v2.test_full_pipeline
"""

import asyncio
import sys
import time
import json
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from log_ai_agent.ai_agent_v2 import GigaChatClient, LogAnalysisPipeline
from log_ai_agent.ai_agent_v2.rag.chroma_manager import ChromaManager
from log_ai_agent.ai_agent_v2.rag.mitre_loader import MitreLoader


# =============================================================================
# Colors for terminal output
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'


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
# Log input functions
# =============================================================================

def get_log_input() -> str:
    """
    Get log content from user interactively.
    
    Returns:
        Log content as string
    """
    print_header("Ввод логов")
    
    print("Выберите способ ввода логов:")
    print("1. Загрузить из файла")
    print("2. Ввести текст вручную")
    print("3. Использовать тестовые логи")
    
    choice = input(f"\n{Colors.CYAN}Ваш выбор (1/2/3): {Colors.RESET}").strip()
    
    if choice == "1":
        return load_log_from_file()
    elif choice == "2":
        return enter_log_manually()
    elif choice == "3":
        return use_sample_logs()
    else:
        print_warning("Неверный выбор, используем тестовые логи")
        return use_sample_logs()


def load_log_from_file() -> str:
    """Load log content from file."""
    file_path = input(f"{Colors.CYAN}Путь к файлу: {Colors.RESET}").strip()
    
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        # Try different encodings
        for encoding in ['utf-8', 'windows-1251', 'cp866']:
            try:
                content = path.read_text(encoding=encoding)
                print_success(f"Файл загружен: {file_path} ({len(content)} байт)")
                return content
            except UnicodeDecodeError:
                continue
        
        raise ValueError("Не удалось декодировать файл (попробуйте UTF-8 или Windows-1251)")
        
    except Exception as e:
        print_error(f"Ошибка загрузки файла: {e}")
        print_warning("Используем тестовые логи")
        return use_sample_logs()


def enter_log_manually() -> str:
    """Enter log content manually."""
    print("\nВведите текст логов (для завершения введите пустую строку или 'END'):")
    print_separator()
    
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "" or line.strip().upper() == "END":
                break
            lines.append(line)
        except EOFError:
            break
    
    content = "\n".join(lines)
    print_success(f"Введено {len(content)} байт")
    return content


def use_sample_logs() -> str:
    """Use sample log content for testing."""
    sample_log = """2026-03-21 10:15:23 INFO Application started successfully
2026-03-21 10:15:45 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:46 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:47 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:48 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:15:49 WARNING Failed login attempt for user admin from 192.168.1.100
2026-03-21 10:16:00 ERROR SQL syntax error near 'SELECT * FROM users WHERE id=1 OR 1=1--'
2026-03-21 10:16:01 CRITICAL Database connection pool exhausted
2026-03-21 10:16:15 WARNING Suspicious file access: /etc/passwd
2026-03-21 10:16:20 ERROR Unauthorized API request from 10.0.0.55 to /admin/config
2026-03-21 10:16:25 CRITICAL Possible data exfiltration detected: large outbound transfer to 203.0.113.50
2026-03-21 10:16:30 WARNING Privilege escalation attempt by user guest
2026-03-21 10:16:35 ERROR Authentication bypass detected in /api/v1/users endpoint"""
    
    print_success("Используем тестовые логи (1200 байт)")
    return sample_log


# =============================================================================
# ChromaDB initialization
# =============================================================================

async def initialize_chromadb(use_rag: bool = True) -> tuple[Optional[ChromaManager], bool]:
    """
    Initialize ChromaDB with MITRE ATT&CK knowledge base.
    
    Args:
        use_rag: Whether to initialize RAG
        
    Returns:
        Tuple of (ChromaManager, is_available)
    """
    if not use_rag:
        print_warning("RAG отключен пользователем")
        return None, False
    
    print_stage(1, 4, "Инициализация ChromaDB с MITRE ATT&CK")
    
    try:
        # Initialize ChromaDB manager
        chroma_path = Path(__file__).parent / "chroma_db_test"
        print(f"Путь к ChromaDB: {chroma_path}")
        
        chroma_mgr = ChromaManager(
            chroma_path=str(chroma_path),
            embedding_model="sentence-transformers/rubert-base-cased",
        )
        
        # Try to initialize with local embeddings
        print("Загрузка эмбеддингов...")
        if not chroma_mgr.initialize(use_local_model=False):
            print_warning("Не удалось загрузить эмбеддинги")
            print("RAG будет работать в ограниченном режиме")
            return chroma_mgr, False
        
        print_success("ChromaDB инициализирована")
        
        # Check if collection has data
        if chroma_mgr.vectorstore:
            try:
                collection = chroma_mgr.vectorstore._client.get_collection(
                    name=chroma_mgr.collection_name
                )
                count = collection.count()
                
                if count == 0:
                    print_warning("База знаний MITRE пуста")
                    print("Требуется инициализация (это займёт несколько минут)...")
                    
                    # Load MITRE data
                    loader = MitreLoader(chroma_mgr)
                    if loader.load_mitre_data("enterprise-attack"):
                        added = loader.populate_chromadb()
                        print_success(f"Загружено {added} техник MITRE ATT&CK")
                    else:
                        print_error("Не удалось загрузить MITRE ATT&CK")
                        return chroma_mgr, False
                else:
                    print_success(f"В базе знаний {count} техник MITRE ATT&CK")
                    
            except Exception as e:
                print_warning(f"Ошибка проверки коллекции: {e}")
                return chroma_mgr, False
        
        return chroma_mgr, True
        
    except Exception as e:
        print_error(f"Ошибка инициализации ChromaDB: {e}")
        print_warning("Продолжаем без RAG")
        return None, False


# =============================================================================
# Pipeline execution
# =============================================================================

async def run_pipeline(
    log_content: str,
    chroma_mgr: Optional[ChromaManager],
    use_rag: bool,
) -> dict:
    """
    Run complete analysis pipeline with detailed output.
    
    Args:
        log_content: Log content to analyze
        chroma_mgr: ChromaDB manager (or None)
        use_rag: Whether to use RAG
        
    Returns:
        Dictionary with all intermediate results
    """
    results = {
        "log_size": len(log_content),
        "stages": {},
        "total_time": 0,
    }
    
    # Initialize GigaChat client
    client = GigaChatClient(
        temperature=0.1,
        max_tokens=4000,
        timeout=90,
        rate_limit_delay=0.5,
    )
    
    # Create pipeline
    pipeline = LogAnalysisPipeline(
        gigachat_client=client,
        chroma_manager=chroma_mgr if use_rag else None,
        rag_top_k=5,
        use_rag=use_rag,
    )
    
    # Run analysis
    start_time = time.time()
    result = await pipeline.analyze_log(log_content, timeout_seconds=180)
    total_time = time.time() - start_time
    
    results["total_time"] = total_time
    results["success"] = result.success
    
    if result.success:
        # Extract intermediate results
        if result.primary_analysis:
            results["stages"]["agent1"] = {
                "success": result.primary_analysis.success,
                "text": result.primary_analysis.analysis_text,
                "events_found": result.primary_analysis.events_found,
                "time_ms": result.primary_analysis.processing_time_ms,
            }
        
        if result.mitre_result:
            results["stages"]["rag"] = {
                "success": result.mitre_result.success,
                "techniques": result.mitre_result.techniques,
                "context": result.mitre_result.context_text,
                "time_ms": result.mitre_result.processing_time_ms,
            }
        
        if result.final_result:
            results["stages"]["agent2"] = {
                "success": result.final_result.success,
                "report": result.final_result.report_text,
                "severity": result.final_result.severity_level_id,
                "threat": result.final_result.threat_type_id,
                "mitre_techniques": result.final_result.mitre_techniques,
                "time_ms": result.final_result.processing_time_ms,
            }
    
    await client.close()
    
    return results


# =============================================================================
# Output formatting
# =============================================================================

def print_results(results: dict):
    """Print pipeline results with detailed output."""
    
    print_header("Результаты анализа")
    
    if not results.get("success"):
        print_error("Анализ не удался")
        return
    
    # Stage 1: Agent 1
    print_stage(2, 4, "Первичный анализ логов (Агент 1)")
    print_separator()
    
    if "agent1" in results["stages"]:
        agent1 = results["stages"]["agent1"]
        print_success(f"Найдено событий: {agent1['events_found']}")
        print(f"Время выполнения: {agent1['time_ms']:.0f} мс")
        print_separator()
        print(f"{Colors.CYAN}{agent1['text']}{Colors.RESET}")
    else:
        print_warning("Нет результатов от Агента 1")
    
    # Stage 2: RAG
    print_stage(3, 4, "Поиск техник MITRE (RAG)")
    print_separator()
    
    if "rag" in results["stages"]:
        rag = results["stages"]["rag"]
        if rag["success"]:
            print_success(f"Найдено техник: {len(rag['techniques'])}")
            print(f"Время выполнения: {rag['time_ms']:.0f} мс")
            print_separator()
            
            for i, tech in enumerate(rag["techniques"], 1):
                tech_id = tech.get("id", "N/A")
                tech_name = tech.get("name", "N/A")
                tactic = tech.get("tactic", "N/A")
                print(f"  {i}. {Colors.YELLOW}{tech_id}{Colors.RESET}: {tech_name}")
                print(f"     Тактика: {tactic}")
            
            print_separator()
            print(f"{Colors.CYAN}Контекст:{Colors.RESET}")
            print(f"{rag['context']}")
        else:
            print_warning(f"RAG не удался: {rag.get('error', 'Unknown error')}")
    else:
        print_warning("RAG отключен")
    
    # Stage 3: Agent 2
    print_stage(4, 4, "Финальный отчёт (Агент 2)")
    print_separator()
    
    if "agent2" in results["stages"]:
        agent2 = results["stages"]["agent2"]
        
        # Severity and threat
        severity_names = {1: "Критический", 2: "Высокий", 3: "Средний", 4: "Низкий"}
        threat_names = {
            1: "Вторжение", 2: "Malware", 3: "DDoS", 4: "Утечка",
            5: "Доступ", 6: "Фишинг", 7: "SQL", 8: "XSS", 9: "Брутфорс",
            10: "Сканирование", 11: "Другое"
        }
        
        severity_color = Colors.RED if agent2["severity"] == 1 else (
            Colors.YELLOW if agent2["severity"] == 2 else Colors.GREEN
        )
        
        print(f"Уровень серьезности: {severity_color}{agent2['severity']}/4 ({severity_names.get(agent2['severity'], 'N/A')}){Colors.RESET}")
        print(f"Тип угрозы: {Colors.YELLOW}{agent2['threat']}/11 ({threat_names.get(agent2['threat'], 'N/A')}){Colors.RESET}")
        
        if agent2["mitre_techniques"]:
            print(f"MITRE техники: {Colors.CYAN}{', '.join(agent2['mitre_techniques'])}{Colors.RESET}")
        
        print(f"Время выполнения: {agent2['time_ms']:.0f} мс")
        print_separator()
        print(f"{Colors.CYAN}{agent2['report']}{Colors.RESET}")
    else:
        print_warning("Нет результатов от Агента 2")
    
    # Summary
    print_header("Итоги")
    print(f"Общий размер логов: {results['log_size']} байт")
    print(f"Общее время анализа: {Colors.YELLOW}{results['total_time']:.1f} сек{Colors.RESET}")
    
    if "agent1" in results["stages"] and "agent2" in results["stages"]:
        t1 = results["stages"]["agent1"]["time_ms"]
        t2 = results["stages"]["agent2"]["time_ms"]
        rag_time = results["stages"].get("rag", {}).get("time_ms", 0)
        print(f"  - Агент 1: {t1:.0f} мс")
        print(f"  - RAG: {rag_time:.0f} мс")
        print(f"  - Агент 2: {t2:.0f} мс")


def save_results(results: dict, output_path: Optional[str] = None):
    """Save results to JSON file."""
    if not output_path:
        return
    
    try:
        path = Path(output_path)
        
        # Prepare export data (remove large text fields)
        export_data = {
            "success": results.get("success", False),
            "log_size": results.get("log_size", 0),
            "total_time_sec": results.get("total_time", 0),
            "summary": {},
        }
        
        if "agent1" in results.get("stages", {}):
            export_data["summary"]["agent1"] = {
                "events_found": results["stages"]["agent1"]["events_found"],
                "time_ms": results["stages"]["agent1"]["time_ms"],
            }
        
        if "rag" in results.get("stages", {}):
            export_data["summary"]["rag"] = {
                "techniques_count": len(results["stages"]["rag"]["techniques"]),
                "time_ms": results["stages"]["rag"]["time_ms"],
            }
        
        if "agent2" in results.get("stages", {}):
            export_data["summary"]["agent2"] = {
                "severity": results["stages"]["agent2"]["severity"],
                "threat": results["stages"]["agent2"]["threat"],
                "mitre_techniques": results["stages"]["agent2"]["mitre_techniques"],
                "time_ms": results["stages"]["agent2"]["time_ms"],
            }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print_success(f"Результаты сохранены: {output_path}")
        
    except Exception as e:
        print_error(f"Ошибка сохранения: {e}")


# =============================================================================
# Main function
# =============================================================================

async def main():
    """Main entry point."""
    print_header("AI Agent v2 - Полный тест пайплайна")
    
    # Get configuration
    print("Настройки:")
    use_rag_input = input(f"{Colors.CYAN}Использовать RAG? (y/n, по умолчанию y): {Colors.RESET}").strip().lower()
    use_rag = use_rag_input != "n"
    
    save_output = input(f"{Colors.CYAN}Сохранить результаты в файл? (y/n, по умолчанию n): {Colors.RESET}").strip().lower()
    output_file = None
    if save_output == "y":
        output_file = input(f"{Colors.CYAN}Имя файла (по умолчанию results.json): {Colors.RESET}").strip()
        if not output_file:
            output_file = "results.json"
    
    # Get log input
    log_content = get_log_input()
    
    print_separator()
    
    # Initialize ChromaDB
    chroma_mgr, rag_available = await initialize_chromadb(use_rag)
    
    if not rag_available and use_rag:
        print_warning("RAG недоступен, продолжаем без него")
    
    # Run pipeline
    results = await run_pipeline(
        log_content=log_content,
        chroma_mgr=chroma_mgr,
        use_rag=use_rag and rag_available,
    )
    
    # Print results
    print_results(results)
    
    # Save if requested
    if output_file:
        save_results(results, output_file)
    
    print_header("Тест завершён")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Прервано пользователем{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Ошибка: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

"""Оценка качества AI-агента на размеченном тестовом наборе логов.

Скрипт прогоняет все 100 логов через analyze_log_with_gigachat и сравнивает
результаты с эталонной разметкой для расчета метрик качества.
"""

import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Добавляем путь к модулю log_ai_agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from log_ai_agent.ai_agent.gigachat import analyze_log_with_gigachat


def calculate_metrics(results: list[dict]) -> dict:
    """Рассчитать метрики качества классификации.

    Args:
        results: Список результатов с actual и predicted значениями

    Returns:
        Словарь с метриками

    """
    total = len(results)

    # Общая точность (accuracy)
    correct_severity = sum(1 for r in results if r["match_severity"])
    correct_threat = sum(1 for r in results if r["match_threat"])
    correct_both = sum(1 for r in results if r["match_severity"] and r["match_threat"])

    accuracy_severity = correct_severity / total if total > 0 else 0
    accuracy_threat = correct_threat / total if total > 0 else 0
    accuracy_both = correct_both / total if total > 0 else 0

    # Confusion matrix для каждого класса
    severity_confusion = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
    threat_confusion = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})

    for r in results:
        # Severity
        for level in [1, 2, 3, 4]:
            if r["actual_severity"] == level and r["predicted_severity"] == level:
                severity_confusion[level]["tp"] += 1
            elif r["actual_severity"] == level and r["predicted_severity"] != level:
                severity_confusion[level]["fn"] += 1
            elif r["actual_severity"] != level and r["predicted_severity"] == level:
                severity_confusion[level]["fp"] += 1
            else:
                severity_confusion[level]["tn"] += 1

        # Threat type
        for threat_id in range(1, 12):
            if r["actual_threat"] == threat_id and r["predicted_threat"] == threat_id:
                threat_confusion[threat_id]["tp"] += 1
            elif r["actual_threat"] == threat_id and r["predicted_threat"] != threat_id:
                threat_confusion[threat_id]["fn"] += 1
            elif r["actual_threat"] != threat_id and r["predicted_threat"] == threat_id:
                threat_confusion[threat_id]["fp"] += 1
            else:
                threat_confusion[threat_id]["tn"] += 1

    # Precision, Recall, F1 для severity
    severity_metrics = {}
    for level in [1, 2, 3, 4]:
        tp = severity_confusion[level]["tp"]
        fp = severity_confusion[level]["fp"]
        fn = severity_confusion[level]["fn"]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        severity_metrics[level] = {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "support": tp + fn,  # Количество реальных примеров этого класса
        }

    # Precision, Recall, F1 для threat type
    threat_metrics = {}
    for threat_id in range(1, 12):
        tp = threat_confusion[threat_id]["tp"]
        fp = threat_confusion[threat_id]["fp"]
        fn = threat_confusion[threat_id]["fn"]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        threat_metrics[threat_id] = {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "support": tp + fn,
        }

    return {
        "total_samples": total,
        "accuracy": {
            "severity": accuracy_severity,
            "threat_type": accuracy_threat,
            "both_correct": accuracy_both,
        },
        "severity_metrics": severity_metrics,
        "threat_metrics": threat_metrics,
        "confusion_matrices": {
            "severity": dict(severity_confusion),
            "threat": dict(threat_confusion),
        },
    }


async def evaluate_single_log(log_path: Path, log_meta: dict) -> dict:
    """Оценить один лог-файл.

    Args:
        log_path: Путь к лог-файлу
        log_meta: Метаданные лога (эталонная разметка)

    Returns:
        Результат оценки

    """
    try:
        # Читаем лог
        with open(log_path, encoding="utf-8") as f:
            log_content = f.read()

        # Анализируем через GigaChat
        prediction = await analyze_log_with_gigachat(log_content)

        # Сравниваем с эталоном
        result = {
            "log_id": log_meta["log_id"],
            "filename": log_meta["filename"],
            "actual_severity": log_meta["severity_level_id"],
            "predicted_severity": prediction["severity_level_id"],
            "actual_threat": log_meta["threat_type_id"],
            "predicted_threat": prediction["threat_type_id"],
            "match_severity": log_meta["severity_level_id"]
            == prediction["severity_level_id"],
            "match_threat": log_meta["threat_type_id"] == prediction["threat_type_id"],
            "success": True,
            "error": None,
            "token_limit": False,
        }

        return result

    except Exception as e:
        error_msg = str(e).lower()
        is_token_limit = any(
            keyword in error_msg
            for keyword in [
                "token",
                "limit",
                "quota",
                "exceeded",
                "токен",
                "лимит",
                "превышен",
            ]
        )

        return {
            "log_id": log_meta["log_id"],
            "filename": log_meta["filename"],
            "actual_severity": log_meta["severity_level_id"],
            "predicted_severity": None,
            "actual_threat": log_meta["threat_type_id"],
            "predicted_threat": None,
            "match_severity": False,
            "match_threat": False,
            "success": False,
            "error": str(e),
            "token_limit": is_token_limit,
        }


async def evaluate_test_set(
    test_logs_dir: str = "test_logs", output_file: str = "evaluation_results.json"
):
    """Оценить AI-агент на всем тестовом наборе.

    Args:
        test_logs_dir: Директория с тестовыми логами
        output_file: Файл для сохранения результатов

    """
    test_path = Path(test_logs_dir)
    labels_file = test_path / "labels.json"

    # Загружаем метаданные
    print("=" * 80)
    print("  Оценка качества AI-агента на тестовом наборе")
    print("=" * 80)
    print()

    with open(labels_file, encoding="utf-8") as f:
        labels_data = json.load(f)

    logs_meta = labels_data["logs"]
    total_logs = len(logs_meta)

    print(f"📊 Загружено {total_logs} тестовых логов")
    print(f"📁 Директория: {test_path.absolute()}")
    print()
    print("🔄 Начинаем анализ...")
    print()

    # Анализируем каждый лог
    results = []
    successful = 0
    failed = 0
    token_limit_reached = False

    for i, log_meta in enumerate(logs_meta, 1):
        log_file = test_path / log_meta["filename"]

        print(f"[{i:3d}/{total_logs}] {log_meta['filename']:40s} ", end="", flush=True)

        result = await evaluate_single_log(log_file, log_meta)
        results.append(result)

        if result["success"]:
            successful += 1
            # Показываем результат сравнения
            severity_icon = "✅" if result["match_severity"] else "❌"
            threat_icon = "✅" if result["match_threat"] else "❌"
            print(f"{severity_icon} Severity  {threat_icon} Threat")

            # Если есть несовпадения, показываем детали
            if not result["match_severity"] or not result["match_threat"]:
                details = []
                if not result["match_severity"]:
                    details.append(
                        f"Severity: ожидалось {result['actual_severity']}, получено {result['predicted_severity']}"
                    )
                if not result["match_threat"]:
                    details.append(
                        f"Threat: ожидалось {result['actual_threat']}, получено {result['predicted_threat']}"
                    )
                print(f"           → {' | '.join(details)}")
        else:
            failed += 1
            if result.get("token_limit", False):
                token_limit_reached = True
                print(f"⚠️  ЛИМИТ ТОКЕНОВ: {result['error'][:50]}")
                print()
                print("⚠️" * 40)
                print("   Исчерпан лимит токенов GigaChat API!")
                print(f"   Успешно обработано: {successful}/{i} логов")
                print("   Оценка будет произведена на доступных данных.")
                print("⚠️" * 40)
                print()
                break  # Прерываем цикл
            else:
                print(f"❌ ОШИБКА: {result['error'][:50]}")

    print()
    print("=" * 80)
    if token_limit_reached:
        print("⚠️  Анализ прерван из-за лимита токенов!")
        print(f"   Проанализировано: {successful + failed}/{total_logs} логов")
    else:
        print("✅ Анализ завершен!")
    print(f"   Успешно: {successful}/{len(results)}")
    print(f"   Ошибок: {failed}/{len(results)}")
    if token_limit_reached:
        print(f"   📊 Метрики рассчитаны на {successful} успешно обработанных логах")
    print("=" * 80)
    print()

    # Рассчитываем метрики
    if successful > 0:
        print("📊 Рассчитываем метрики качества...")
        metrics = calculate_metrics([r for r in results if r["success"]])

        # Выводим основные метрики
        print()
        print("=" * 80)
        print("  МЕТРИКИ КАЧЕСТВА")
        print("=" * 80)
        print()

        print("📈 Общая точность (Accuracy):")
        print(f"   Severity Level:  {metrics['accuracy']['severity']:.2%}")
        print(f"   Threat Type:     {metrics['accuracy']['threat_type']:.2%}")
        print(f"   Оба правильно:   {metrics['accuracy']['both_correct']:.2%}")
        print()

        # Severity metrics
        print("🔴 Метрики по уровням серьезности (Severity):")
        severity_names = {1: "Критический", 2: "Высокий", 3: "Средний", 4: "Низкий"}
        for level, name in severity_names.items():
            m = metrics["severity_metrics"][level]
            if m["support"] > 0:
                print(
                    f"   {level}. {name:12s} - P: {m['precision']:.2%}  R: {m['recall']:.2%}  F1: {m['f1_score']:.2%}  (n={m['support']})"
                )
        print()

        # Threat type metrics
        print("🎯 Метрики по типам угроз (Threat Type):")
        threat_names = labels_data["threat_types"]
        for threat_id, threat_info in sorted(
            threat_names.items(), key=lambda x: int(x[0])
        ):
            threat_id = int(threat_id)
            m = metrics["threat_metrics"][threat_id]
            if m["support"] > 0:
                print(
                    f"   {threat_id:2d}. {threat_info['name']:15s} - P: {m['precision']:.2%}  R: {m['recall']:.2%}  F1: {m['f1_score']:.2%}  (n={m['support']})"
                )
        print()

        # Средние метрики
        avg_severity_f1 = (
            sum(
                m["f1_score"]
                for m in metrics["severity_metrics"].values()
                if m["support"] > 0
            )
            / 4
        )
        avg_threat_f1 = (
            sum(
                m["f1_score"]
                for m in metrics["threat_metrics"].values()
                if m["support"] > 0
            )
            / 11
        )

        print("📊 Средние метрики:")
        print(f"   Severity F1-Score: {avg_severity_f1:.2%}")
        print(f"   Threat F1-Score:   {avg_threat_f1:.2%}")
        print()

        # Сохраняем результаты
        output_data = {
            "evaluated_at": datetime.now().isoformat(),
            "total_logs": total_logs,
            "processed_logs": len(results),
            "successful": successful,
            "failed": failed,
            "token_limit_reached": token_limit_reached,
            "metrics": metrics,
            "detailed_results": results,
        }

        output_path = test_path / output_file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print("=" * 80)
        print(f"💾 Результаты сохранены: {output_path}")
        print("=" * 80)

    else:
        print("❌ Не удалось проанализировать ни одного лога успешно")


async def main():
    """Основная функция."""
    await evaluate_test_set()


if __name__ == "__main__":
    asyncio.run(main())

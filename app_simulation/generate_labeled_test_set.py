"""Генератор размеченных тестовых логов для оценки качества AI-агента.

Создает набор из 100 лог-файлов с известной разметкой (severity_level_id, threat_type_id)
для последующей оценки точности классификации.
"""

import json
import random
from datetime import datetime
from pathlib import Path

from log_gen.config_loader import ConfigLoader
from log_gen.log_gen import LogGenerator

# Определяем типы угроз согласно системе
THREAT_TYPES = {
    1: {"name": "Вторжение", "description": "Intrusion - попытки несанкционированного доступа"},
    2: {"name": "Malware", "description": "Вредоносное ПО - вирусы, трояны, черви"},
    3: {"name": "DDoS", "description": "Распределенная атака отказа в обслуживании"},
    4: {"name": "Утечка", "description": "Утечка данных - несанкционированный доступ к конфиденциальной информации"},
    5: {"name": "Доступ", "description": "Несанкционированный доступ - нарушение прав доступа"},
    6: {"name": "Фишинг", "description": "Фишинговые атаки - социальная инженерия"},
    7: {"name": "SQL", "description": "SQL-инъекция - эксплуатация уязвимостей БД"},
    8: {"name": "XSS", "description": "Cross-Site Scripting - межсайтовый скриптинг"},
    9: {"name": "Брутфорс", "description": "Brute Force - перебор паролей"},
    10: {"name": "Сканирование", "description": "Сканирование портов и служб"},
    11: {"name": "Другое", "description": "Другие типы угроз"},
}

SEVERITY_LEVELS = {
    1: "Критический",
    2: "Высокий",
    3: "Средний",
    4: "Низкий",
}

# Сопоставление конфигураций с типами угроз
LABELED_SCENARIOS = [
    # 1. Вторжение (Intrusion)
    {
        "config": "log_gen/configs/labeled/intrusion.json",
        "threat_type_id": 1,
        "severity_level_id": 1,  # Критический
        "count": 10,
        "description": "Попытки несанкционированного проникновения в систему",
    },
    # 2. Malware
    {
        "config": "log_gen/configs/labeled/malware.json",
        "threat_type_id": 2,
        "severity_level_id": 1,  # Критический
        "count": 8,
        "description": "Обнаружение активности вредоносного ПО",
    },
    # 3. DDoS
    {
        "config": "log_gen/configs/labeled/ddos.json",
        "threat_type_id": 3,
        "severity_level_id": 1,  # Критический
        "count": 8,
        "description": "Распределенная атака отказа в обслуживании",
    },
    # 4. Утечка данных
    {
        "config": "log_gen/configs/labeled/data_breach.json",
        "threat_type_id": 4,
        "severity_level_id": 1,  # Критический
        "count": 8,
        "description": "Попытки несанкционированного доступа к конфиденциальным данным",
    },
    # 5. Несанкционированный доступ
    {
        "config": "log_gen/configs/labeled/unauthorized_access.json",
        "threat_type_id": 5,
        "severity_level_id": 2,  # Высокий
        "count": 10,
        "description": "Нарушения прав доступа к ресурсам",
    },
    # 6. Фишинг
    {
        "config": "log_gen/configs/labeled/phishing.json",
        "threat_type_id": 6,
        "severity_level_id": 2,  # Высокий
        "count": 8,
        "description": "Фишинговые атаки и социальная инженерия",
    },
    # 7. SQL-инъекция
    {
        "config": "log_gen/configs/labeled/sql_injection.json",
        "threat_type_id": 7,
        "severity_level_id": 1,  # Критический
        "count": 10,
        "description": "Попытки SQL-инъекций",
    },
    # 8. XSS
    {
        "config": "log_gen/configs/labeled/xss.json",
        "threat_type_id": 8,
        "severity_level_id": 2,  # Высокий
        "count": 8,
        "description": "Попытки межсайтового скриптинга",
    },
    # 9. Брутфорс
    {
        "config": "log_gen/configs/labeled/brute_force.json",
        "threat_type_id": 9,
        "severity_level_id": 2,  # Высокий
        "count": 12,
        "description": "Попытки перебора паролей",
    },
    # 10. Сканирование портов
    {
        "config": "log_gen/configs/labeled/port_scan.json",
        "threat_type_id": 10,
        "severity_level_id": 3,  # Средний
        "count": 10,
        "description": "Сканирование портов и служб",
    },
    # 11. Другое (смешанные/нормальные логи)
    {
        "config": "log_gen/configs/stable.json",
        "threat_type_id": 11,
        "severity_level_id": 4,  # Низкий
        "count": 8,
        "description": "Обычная активность без явных угроз",
    },
]


def generate_labeled_test_set(output_dir: str = "test_logs"):
    """Генерирует набор размеченных тестовых логов.
    
    Args:
        output_dir: Директория для сохранения логов
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Создаем файл с общей метаинформацией
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "total_logs": sum(scenario["count"] for scenario in LABELED_SCENARIOS),
        "threat_types": THREAT_TYPES,
        "severity_levels": SEVERITY_LEVELS,
        "scenarios": LABELED_SCENARIOS,
        "logs": []
    }
    
    log_counter = 1
    
    print("=" * 80)
    print("  Генерация размеченных тестовых логов")
    print("=" * 80)
    print()
    
    for scenario in LABELED_SCENARIOS:
        config_path = scenario["config"]
        threat_type = THREAT_TYPES[scenario["threat_type_id"]]
        severity_level = SEVERITY_LEVELS[scenario["severity_level_id"]]
        
        print(f"📊 Сценарий: {threat_type['name']} ({scenario['description']})")
        print(f"   Уровень: {severity_level} (ID={scenario['severity_level_id']})")
        print(f"   Тип угрозы: ID={scenario['threat_type_id']}")
        print(f"   Количество: {scenario['count']} файлов")
        
        try:
            # Загружаем конфигурацию
            config = ConfigLoader.load_from_json(config_path)
            
            # Генерируем логи для этого сценария
            for i in range(scenario["count"]):
                generator = LogGenerator(config)
                log_entries = generator.generate_logs()
                
                # Формируем имя файла
                filename = f"log_{log_counter:03d}_{threat_type['name'].lower()}.log"
                log_file_path = output_path / filename
                
                # Сохраняем лог-файл
                with open(log_file_path, "w", encoding="utf-8") as f:
                    for entry in log_entries:
                        f.write(entry.format() + "\n")
                
                # Добавляем метаданные для этого лога
                log_metadata = {
                    "log_id": log_counter,
                    "filename": filename,
                    "threat_type_id": scenario["threat_type_id"],
                    "threat_type_name": threat_type["name"],
                    "severity_level_id": scenario["severity_level_id"],
                    "severity_level_name": severity_level,
                    "description": scenario["description"],
                    "config_used": config_path,
                    "line_count": len(log_entries),
                }
                
                metadata["logs"].append(log_metadata)
                log_counter += 1
            
            print(f"   ✅ Сгенерировано {scenario['count']} файлов")
            
        except FileNotFoundError:
            print(f"   ⚠️  Конфигурация не найдена: {config_path}")
            print(f"   ℹ️  Пропускаем этот сценарий")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        print()
    
    # Сохраняем метаданные в JSON
    metadata_file = output_path / "labels.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print("=" * 80)
    print(f"✅ Генерация завершена!")
    print(f"📁 Директория: {output_path.absolute()}")
    print(f"📊 Всего файлов: {log_counter - 1}")
    print(f"📋 Метаданные: {metadata_file}")
    print("=" * 80)
    print()
    print("Распределение по типам угроз:")
    for threat_id, threat_info in THREAT_TYPES.items():
        count = sum(s["count"] for s in LABELED_SCENARIOS if s["threat_type_id"] == threat_id)
        if count > 0:
            print(f"  {threat_id}. {threat_info['name']:20s} - {count:3d} файлов")
    print()


if __name__ == "__main__":
    generate_labeled_test_set()

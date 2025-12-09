import os
import re

import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor

SALT = bcrypt.gensalt(rounds=12)


def get_db_connection():
    """Создать подключение к PostgreSQL базе данных.

    Returns:
        psycopg2.connection: Подключение к базе данных.

    Raises:
        Exception: Если не удалось подключиться к БД.

    """
    try:
        # Получаем параметры подключения из переменных окружения
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5433"),
            database=os.getenv("POSTGRES_DB", "cyberlog_db"),
            user=os.getenv("POSTGRES_USER", "cyberlog_user"),
            password=os.getenv("POSTGRES_PASSWORD", "cyberlog_password"),
        )
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        raise


def validate_login(login: str) -> tuple[bool, str]:
    """Валидация логина пользователя.

    Args:
        login: Логин для проверки.

    Returns:
        tuple: (валидность, сообщение об ошибке)

    Rules:
        - От 6 до 16 символов
        - Не должен начинаться с цифры
        - Не должен состоять только из цифр
        - Только английские буквы и цифры (без специальных символов)

    """
    if len(login) < 6:
        return False, "Логин должен содержать минимум 6 символов"

    if len(login) > 16:
        return False, "Логин должен содержать максимум 16 символов"

    if not re.match(r"^[a-zA-Z0-9]+$", login):
        return False, "Логин может содержать только английские буквы и цифры"

    if login[0].isdigit():
        return False, "Логин не должен начинаться с цифры"

    if login.isdigit():
        return False, "Логин не может состоять только из цифр"

    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """Валидация пароля пользователя.

    Args:
        password: Пароль для проверки.

    Returns:
        tuple: (валидность, сообщение об ошибке)

    Rules:
        - От 8 до 32 символов
        - Должен содержать минимум одну цифру
        - Должен содержать минимум одну букву
        - Должен содержать минимум один специальный символ

    """
    if len(password) < 8:
        return False, "Пароль должен содержать минимум 8 символов"

    if len(password) > 32:
        return False, "Пароль должен содержать максимум 32 символа"

    if not re.search(r"[0-9]", password):
        return False, "Пароль должен содержать минимум одну цифру"

    if not re.search(r"[a-zA-Z]", password):
        return False, "Пароль должен содержать минимум одну букву"

    if not re.search(r"[^a-zA-Z0-9]", password):
        return False, "Пароль должен содержать минимум один специальный символ"

    return True, ""


def collect_logs():
    """Collect analyse_logs from the specified directory."""
    print("Logs collected\n")  # ЗАГЛУШКА >>>


def hide_logs():
    """Hide the analyse_logs from view."""
    print("Logs hidden\n")


def show_logs():
    """Display the analyse_logs."""
    print("Logs shown\n")  # ЗАГЛУШКА >>>


def get_history():
    """Retrieve the incident history."""
    print("Incidents history shown\n")  # ЗАГЛУШКА >>>


def register():
    """Register a new user.

    Prompts for login and password, hashes the password using bcrypt with salt from environment,
    and stores the login and hashed password in the PostgreSQL database (Users table).

    The password salt is retrieved from the PASSWORD_SALT environment variable.
    If the user already exists, the registration is cancelled.

    Note:
        Requires a valid database connection and PASSWORD_SALT environment variable.

    """
    print("\n🔐 Регистрация нового пользователя")
    print("(Для отмены нажмите Enter без ввода)\n")

    # Валидация логина и проверка существования пользователя
    while True:
        login = input("Логин (6-16 символов, буквы и цифры): ").strip()
        if not login:
            print("❌ Регистрация отменена.")
            return

        is_valid, error_message = validate_login(login)
        if not is_valid:
            print(f"❌ {error_message}")
            print(
                "💡 Требования: 6-16 символов, только английские буквы и цифры, не начинается с цифры\n"
            )
            continue

        # Проверяем, существует ли пользователь в БД
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                'SELECT user_id FROM public."Users" WHERE login = %s', (login,)
            )
            existing_user = cursor.fetchone()
            cursor.close()
            conn.close()

            if existing_user:
                print(f"❌ Пользователь с логином '{login}' уже существует\n")
                continue
        except Exception as e:
            print(f"❌ Ошибка при проверке пользователя: {e}\n")
            continue

        break

    # Валидация пароля
    while True:
        password = input("Пароль (8-32 символа, буквы, цифры и символы): ").strip()
        if not password:
            print("❌ Регистрация отменена.")
            return

        is_valid, error_message = validate_password(password)
        if not is_valid:
            print(f"❌ {error_message}")
            print(
                "💡 Требования: 8-32 символа, минимум 1 буква, 1 цифра и 1 специальный символ\n"
            )
            continue
        break

    # Получаем соль из переменной окружения
    password_salt = os.getenv("PASSWORD_SALT")
    if not password_salt:
        print("❌ Ошибка: PASSWORD_SALT не задана в переменных окружения")
        print("💡 Добавьте PASSWORD_SALT в файл .env")
        return

    try:
        # Подключаемся к БД
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Хешируем пароль с использованием соли из переменной окружения
        salt_bytes = password_salt.encode("utf-8")
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        )

        # Вставляем нового пользователя в БД
        cursor.execute(
            'INSERT INTO public."Users" (login, password_hash) VALUES (%s, %s) RETURNING user_id',
            (login, password_hash.decode("utf-8")),
        )
        user_id = cursor.fetchone()["user_id"]

        # Сохраняем изменения
        conn.commit()

        print(f"✅ Пользователь '{login}' успешно зарегистрирован (ID: {user_id})")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Ошибка при регистрации пользователя: {e}")
        if "conn" in locals():
            conn.rollback()
            conn.close()

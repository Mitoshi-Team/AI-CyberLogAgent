import os
import re

import bcrypt
from sqlalchemy import inspect
from log_ai_agent.db.session import get_sync_engine
from sqlalchemy import select
from log_ai_agent.db.session import get_sync_session
from log_ai_agent.db.models import User

SALT = bcrypt.gensalt(rounds=12)


def get_db_connection():
    """Legacy connection method - use get_sync_session() instead.
    
    Kept for backward compatibility but deprecated.
    """
    try:
        engine = get_sync_engine()
        return engine.raw_connection()
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        raise


def _ensure_admin_column(conn=None) -> None:
    """Ensure Users table has is_admin column for admin features."""
    # Use SQLAlchemy inspector to check schema
    try:
        engine = get_sync_engine()
        inspector = inspect(engine)
        cols = inspector.get_columns("Users", schema="public")
        if not any(c["name"] == "is_admin" for c in cols):
            # Use raw connection from engine to execute ALTER
            with engine.raw_connection() as raw_conn:
                with raw_conn.cursor() as cursor:
                    cursor.execute(
                        'ALTER TABLE public."Users" ADD COLUMN is_admin boolean NOT NULL DEFAULT false'
                    )
                    raw_conn.commit()
    except Exception:
        # If fails, leave as-is and let DB handle or caller manage
        return


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


def verify_user_credentials(login: str, password: str) -> tuple[bool, dict | None]:
    """Проверка учетных данных пользователя.

    Args:
        login: Логин пользователя.
        password: Пароль пользователя.

    Returns:
        tuple: (успех, данные пользователя или None)

    """
    try:
        with get_sync_session() as session:
            stmt = select(User).where(User.login == login)
            user_obj = session.execute(stmt).scalar_one_or_none()

            if not user_obj:
                print(f"Пользователь {login} не найден")
                return False, None

            # Проверяем пароль
            password_bytes = password.encode("utf-8")
            stored_hash = user_obj.password_hash

            if isinstance(stored_hash, str):
                stored_hash_bytes = stored_hash.encode("utf-8")
            else:
                stored_hash_bytes = stored_hash

            if bcrypt.checkpw(password_bytes, stored_hash_bytes):
                print(f"Успешная авторизация для {login}")
                return True, {
                    "user_id": user_obj.user_id,
                    "login": user_obj.login,
                    "is_admin": bool(user_obj.is_admin),
                }

            print(f"Неверный пароль для {login}")
            return False, None
    except Exception as e:
        print(f"Ошибка при проверке учетных данных: {e}")
        import traceback

        traceback.print_exc()
        return False, None


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch user by ID for session refresh."""
    try:
        with get_sync_session() as session:
            stmt = select(User).where(User.user_id == user_id)
            user_obj = session.execute(stmt).scalar_one_or_none()
            if not user_obj:
                return None
            return {
                "user_id": user_obj.user_id,
                "login": user_obj.login,
                "is_admin": bool(user_obj.is_admin),
            }
    except Exception:
        return None


def register():
    """Register a new user.

    Prompts for login and password, hashes the password using bcrypt with salt from environment,
    and stores the login and hashed password in the PostgreSQL database (Users table).

    The password salt is retrieved from the PASSWORD_SALT environment variable.
    If the user already exists, the registration is cancelled.

    Note:
        Requires a valid database connection and PASSWORD_SALT environment variable.

    """
    print("\nРегистрация нового пользователя")
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
                "Требования: 6-16 символов, только английские буквы и цифры, не начинается с цифры\n"
            )
            continue

        # Проверяем, существует ли пользователь в БД
        try:
            with get_sync_session() as session:
                stmt = select(User).where(User.login == login)
                existing_user = session.execute(stmt).scalar_one_or_none()
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
                "Требования: 8-32 символа, минимум 1 буква, 1 цифра и 1 специальный символ\n"
            )
            continue
        break

    # Получаем соль из переменной окружения
    password_salt = os.getenv("PASSWORD_SALT")
    if not password_salt:
        print("❌ Ошибка: PASSWORD_SALT не задана в переменных окружения")
        print("Добавьте PASSWORD_SALT в файл .env")
        return

    try:
        # Хешируем пароль
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))

        with get_sync_session() as session:
            # Проверяем на существование (повторная проверка для safety)
            stmt = select(User).where(User.login == login)
            existing = session.execute(stmt).scalar_one_or_none()
            if existing:
                print(f"❌ Пользователь с логином '{login}' уже существует (race)")
                return

            new_user = User(login=login, password_hash=password_hash.decode("utf-8"), is_admin=False)
            session.add(new_user)
            session.commit()

            print(f"✅ Пользователь '{login}' успешно зарегистрирован (ID: {new_user.user_id})")

    except Exception as e:
        print(f"❌ Ошибка при регистрации пользователя: {e}")


def list_users_admin_status() -> list[dict]:
    """Return all users with admin flag."""
    try:
        with get_sync_session() as session:
            stmt = select(User).order_by(User.login.asc())
            users = session.execute(stmt).scalars().all()
            return [
                {"user_id": u.user_id, "login": u.login, "is_admin": bool(u.is_admin)}
                for u in users
            ]
    except Exception:
        return []


def set_user_admin_status(login: str, is_admin: bool) -> tuple[bool, str]:
    """Grant or revoke admin flag for user by login."""
    try:
        with get_sync_session() as session:
            stmt = select(User).where(User.login == login)
            user_obj = session.execute(stmt).scalar_one_or_none()
            if not user_obj:
                return False, f"Пользователь '{login}' не найден"

            user_obj.is_admin = bool(is_admin)
            session.add(user_obj)
            session.commit()
            status_text = "администратор" if user_obj.is_admin else "обычный пользователь"
            return True, f"Пользователь '{user_obj.login}' обновлен: {status_text}"
    except Exception:
        raise

# gigachat_chat.py

import json
import os
from datetime import datetime

import psycopg2

# Используем RAG-обёртку для запросов к GigaChat
from .RAG_gigachat import ask_gigachat

# Database configuration
DB_CONFIG = {
    "host": "localhost",  # Direct connection from host to container
    "port": int(os.getenv("POSTGRES_PORT", 5433)),  # Match docker-compose port mapping
    "database": os.getenv("POSTGRES_DB", "cyberlog_db"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "cyberlog_password"),
}

# Path to RAG context files (JSON)
RAG_CONTEXT_DIR = "rag_context"


def get_db_connection():
    """Establish a connection to the PostgreSQL database."""
    return psycopg2.connect(**DB_CONFIG)


def load_rag_context() -> dict:
    """Load RAG context from JSON files."""
    context = {}
    if not os.path.exists(RAG_CONTEXT_DIR):
        os.makedirs(RAG_CONTEXT_DIR)

    # Load all JSON files from RAG context directory
    for filename in os.listdir(RAG_CONTEXT_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(RAG_CONTEXT_DIR, filename)
            try:
                with open(filepath, encoding="utf-8") as f:
                    # Use filename without extension as key
                    context_key = filename[:-5]  # Remove .json extension
                    context[context_key] = json.load(f)
            except Exception as e:
                print(f"Error loading RAG context file {filename}: {e}")

    return context


def save_message(user_id: int, role: str, content: str):
    """Save a message to the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            'INSERT INTO "Messages" (user_id, role, content, created_at) VALUES (%s, %s, %s, %s)',
            (user_id, role, content, datetime.now()),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_chat_history(user_id: int) -> list[dict]:
    """Retrieve chat history for a user from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            'SELECT role, content, created_at FROM "Messages" WHERE user_id = %s ORDER BY created_at ASC',
            (user_id,),
        )
        rows = cur.fetchall()
        return [
            {"role": row[0], "content": row[1], "created_at": row[2]} for row in rows
        ]
    finally:
        cur.close()
        conn.close()


def process_user_input(user_id: int, user_input: str, rag_context: dict) -> str:
    """Process user input and return appropriate response using GigaChat."""
    # Save user message
    save_message(user_id, "user", user_input)
    # Собираем последние 10 сообщений пользователя как контекст
    try:
        history = get_chat_history(user_id)
        last_msgs = history[-10:]
        history_lines = [f"{m['role']}: {m['content']}" for m in last_msgs]
        history_text = "\n".join(history_lines)

        # Формируем вопрос с контекстом диалога
        formatted_question = (
            f"История диалога:\n{history_text}\nВопрос: {user_input}"
            if history_text
            else f"Вопрос: {user_input}"
        )

        # Use RAG-enabled GigaChat wrapper
        response = ask_gigachat(formatted_question)
    except Exception as e:
        print(f"Error communicating with RAG GigaChat: {e}")
        response = (
            "Извините, произошла ошибка при подключении к нейросети. Попробуйте позже."
        )

    # Save response
    save_message(user_id, "assistant", response)

    return response


def main():
    """Main function to run the chatbot."""
    print("Привет! Я ассистент по кибербезопасности. Введите 'exit' для выхода.")

    # Load RAG context
    rag_context = load_rag_context()

    # Simulate user session
    user_id = 1  # In real application, this would come from authentication

    # Load chat history
    history = get_chat_history(user_id)
    for msg in history:
        print(f"{msg['role']}: {msg['content']}")

    user_input = input("\nВы: ")
    response = process_user_input(user_id, user_input, rag_context)
    print(f"Ассистент: {response}")


if __name__ == "__main__":
    main()

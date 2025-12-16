from langchain_gigachat.chat_models import GigaChat
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

from log_ai_agent.config.cfg import GIGACHAT_API_KEY

# 1. Загружаем локальные эмбеддинги (из распакованной папки model)
# Это исключит ошибки скачивания и блокировки "lock"
embeddings = HuggingFaceEmbeddings(model_name="./model")

# 2. Подключаем векторную базу
vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings,
    collection_name="mitre_collection"
)

# 3. Инициализируем GigaChat
# Замените 'ВАШ_КЛЮЧ' на данные из личного кабинета GigaChat
llm = GigaChat(
    credentials=GIGACHAT_API_KEY,
    verify_ssl_certs=False,
    model="GigaChat", # или GigaChat-Pro / GigaChat-Max
    temperature=0.1   # Ставим низкую температуру для точности
)

# 4. Настраиваем Промпт (чтобы GigaChat отвечал строго по базе MITRE)
template = """Используй предоставленные фрагменты базы знаний MITRE ATT&CK для ответа на вопрос. 
Если ты не знаешь ответа, просто скажи, что не знаешь, не пытайся выдумывать.
Используй максимум три предложения и старайся отвечать кратко.

Контекст: {context}

Вопрос: {question}

Ответ на русском языке:"""

QA_CHAIN_PROMPT = PromptTemplate.from_template(template)

# 5. Создаем цепочку RAG
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 13}),
    chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}
)

def ask_gigachat(question: str) -> str:
    """
    Функция для отправки вопроса в GigaChat с добавлением префикса "query:"
    и получения ответа.
    
    Args:
        question (str): Вопрос от пользователя.
    
    Returns:
        str: Ответ от GigaChat.
    """
    # Добавляем префикс "query: " к вопросу
    formatted_question = f"query: {question}"
    response = qa_chain.invoke(formatted_question)
    return response["result"]

# Пример использования функции
if __name__ == "__main__":
    question = "Как дела?"
    answer = ask_gigachat(question)
    print("--- ОТВЕТ GIGACHAT ---")
    print(answer)
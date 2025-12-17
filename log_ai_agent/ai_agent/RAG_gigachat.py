from langchain.prompts import PromptTemplate
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_gigachat.chat_models import GigaChat
from langchain_huggingface import HuggingFaceEmbeddings
import logging
import os

from log_ai_agent.config.cfg import GIGACHAT_API_KEY

logger = logging.getLogger(__name__)

# Попробуем взять модель из локальной папки рядом с этим файлом
LOCAL_MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")

# 1. Попытка инициализировать локальные эмбеддинги и векторную базу
embeddings = None
vectorstore = None
use_vectorstore = False
try:
    embeddings = HuggingFaceEmbeddings(
        model_name=LOCAL_MODEL_DIR, model_kwargs={"local_files_only": True}
    )
    vectorstore = Chroma(
        persist_directory=os.path.join(os.path.dirname(__file__), "chroma_db"),
        embedding_function=embeddings,
        collection_name="mitre_collection",
    )
    use_vectorstore = True
    logger.info(f"Loaded local embeddings from {LOCAL_MODEL_DIR}")
except Exception as e:
    logger.warning(
        f"Local embeddings not available or failed to load from {LOCAL_MODEL_DIR}: {e}. Falling back to LLM-only mode."
    )

# 3. Инициализируем GigaChat
llm = GigaChat(
    credentials=GIGACHAT_API_KEY,
    verify_ssl_certs=False,
    model="GigaChat",
    temperature=0.1,
)

# 4. Настраиваем Промпт (чтобы GigaChat отвечал строго по базе MITRE)
template = """Используй предоставленные фрагменты базы знаний MITRE ATT&CK для ответа на вопрос. Также в дополнение скажи какая линия (1, 2, 3) занимается такими угрозами. 
Если ты не знаешь ответа, просто скажи, что не знаешь, не пытайся выдумывать.
Используй максимум три предложения и старайся отвечать кратко.

Контекст: {context}

Вопрос: {question}

Ответ на русском языке:"""

QA_CHAIN_PROMPT = PromptTemplate.from_template(template)

# 5. Создаем цепочку RAG
if use_vectorstore and vectorstore is not None:
    rag_chain = (
        {
            "context": vectorstore.as_retriever(search_kwargs={"k": 5}),
            "question": RunnablePassthrough(),
        }
        | QA_CHAIN_PROMPT
        | llm
        | StrOutputParser()
    )
else:
    # Fallback: без векторной БД — просто промпт -> LLM
    rag_chain = QA_CHAIN_PROMPT | llm | StrOutputParser()


def ask_gigachat(question: str) -> str:
    """Функция для отправки вопроса в GigaChat с добавлением префикса "query:"
    и получения ответа.

    Args:
        question (str): Вопрос от пользователя.

    Returns:
        str: Ответ от GigaChat.

    """
    # Добавляем префикс "query: " к вопросу
    formatted_question = f"query: {question}"
    response = rag_chain.invoke(formatted_question)
    return response


# Пример использования функции
if __name__ == "__main__":
    question = "Как injection?"
    answer = ask_gigachat(question)
    print("--- ОТВЕТ GIGACHAT ---")
    print(answer)

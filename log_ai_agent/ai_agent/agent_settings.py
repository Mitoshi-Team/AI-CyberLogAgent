from langchain_community.chat_models import GigaChat
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough


class GigaChatRAG:
    """Class for creating GigaChat instance with RAG configuration."""

    def __init__(
        self,
        credentials: str,
        base_url: str = "https://api.gigachat.ru",
        model: str = "GigaChat",
        temperature: float = 0.5,
    ):
        """Initialize GigaChat RAG instance.

        Args:
            credentials (str): API credentials for GigaChat
            base_url (str): Base URL for GigaChat API
            model (str): Model name
            temperature (float): Temperature for text generation

        """
        self.credentials = credentials
        self.base_url = base_url
        self.model = model
        self.temperature = temperature

        # Initialize GigaChat
        self.llm = GigaChat(
            credentials=self.credentials,
            base_url=self.base_url,
            model=self.model,
            temperature=self.temperature,
            verify_ssl_certs=False,
        )

        self.vectorstore = None
        self.retriever = None
        self.rag_chain = None

    def setup_rag(
        self,
        texts: list,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        """Setup RAG with provided texts.

        Args:
            texts (list): List of text documents for RAG
            embedding_model (str): Name of the embedding model

        """
        # Create embeddings
        embeddings = HuggingFaceEmbeddings(model_name=embedding_model)

        # Create vector store
        self.vectorstore = Chroma.from_texts(texts=texts, embedding=embeddings)

        # Create retriever
        self.retriever = self.vectorstore.as_retriever()

        # Create RAG chain
        prompt_template = """Use the following pieces of context to answer the question at the end.
        If you don't know the answer, just say that you don't know, don't try to make up an answer.

        {context}

        Question: {question}
        Answer:"""
        prompt = ChatPromptTemplate.from_template(prompt_template)

        self.rag_chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def ask(self, question: str) -> str:
        """Ask question using RAG chain.

        Args:
            question (str): Question to ask

        Returns:
            str: Answer from RAG system

        """
        if self.rag_chain is None:
            raise ValueError("RAG system not initialized. Call setup_rag() first.")

        return self.rag_chain.invoke(question)

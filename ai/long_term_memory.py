import logging
from typing import List, Dict
import chromadb
from sentence_transformers import SentenceTransformer
from logger.console import ConsoleLogger


class LongTermMemory:
    """
    RAG-based long-term memory (ChromaDB)
    Stores conversation history and finds relevant memories
    """

    def __init__(self, db_path: str = "./.chroma_memory"):
        self._logger = ConsoleLogger(LongTermMemory.__name__, logging.INFO)

        # Init ChromaDB
        self._logger.info("ChromaDB initializing...")
        self.client = chromadb.PersistentClient(path=db_path)

        # Load embedding model
        self._logger.info("Loading embedding model (this may take a few seconds)...")
        self.embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self._logger.info("Long-term memory is ready")

    def get_collection(self, user_id: int):
        """Get user collection"""
        return self.client.get_or_create_collection(
            name=f"user_{user_id}_memory"
        )

    def save_interaction(self, user_id: int, user_message: str, bot_response: str, metadata: dict = None):
        """
        Save interaction to long-term memory

        Args:
            user_id: ID of user
            user_message: message from user
            bot_response: response from AI

            metadata: additional metadata (date, theme etc.)
        """
        collection = self.get_collection(user_id)

        # get text and create embedding
        text = f"User: {user_message}\nAssistant: {bot_response}"
        embedding = self.embedder.encode(text).tolist()

        # default metadata
        if metadata is None:
            metadata = {}

        # generating unique ID
        doc_id = f"msg_{collection.count()}"

        # saving
        collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )

        self._logger.debug(f"User interaction saved {user_id}")

    def get_relevant_context(self, user_id: int, query: str, n_results: int = 3) -> str:
        """
        Find relevant memories from long-term memory

        Args:
            user_id: user ID
            query: current user request
            n_results: number of relevant memories

        Returns:
            A string with relevant context
        """
        collection = self.get_collection(user_id)

        # checking if there are any saved memories
        if collection.count() == 0:
            self._logger.debug(f"There are no saved memories for user {user_id}")
            return ""

        # create request embedding
        query_embedding = self.embedder.encode(query).tolist()

        # search same memories
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count())
        )

        # create context
        if not results['documents'][0]:
            return ""

        context_parts = []
        for i, doc in enumerate(results['documents'][0], 1):
            context_parts.append(f"[Воспоминание {i}]\n{doc}")

        context = "=== Несколько сообщений твоего предыдущего диалога с пользователем (ты - Assistant, пользователь - User) ===\n\n"
        context += "\n\n".join(context_parts)
        context += "\n\n=== Конец сообщений предыдущего диалога ==="

        self._logger.debug(f"Found {len(results['documents'][0])} relevant memories")

        return context

    def clear_memory(self, user_id: int):
        """Clear long-term memory for user dialog"""
        try:
            self.client.delete_collection(f"user_{user_id}_memory")
            self._logger.info(f"Long-term memory of user {user_id} dialog was cleared")
        except Exception as e:
            self._logger.warning(f"Unable to clear memory of user dialog: {e}")

    def get_memory_stats(self, user_id: int) -> Dict:
        """Get users dialog memory statistics"""
        collection = self.get_collection(user_id)
        return {
            "total_interactions": collection.count(),
            "user_id": user_id
        }

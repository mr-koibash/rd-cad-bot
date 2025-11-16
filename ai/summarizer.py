import logging
from typing import List, Dict

from ai.prompts import summary_prompt
from logger.console import ConsoleLogger
from ai.llm import Llm


class DialogSummarizer:
    """
    Dialogue Summarizer
    Periodically condenses a story into a short summary
    """

    def __init__(self, llm: Llm):
        self._llm = llm
        self._logger = ConsoleLogger(DialogSummarizer.__name__, logging.INFO)

        # Settings
        self.MESSAGES_PER_SUMMARY = 15  # Create summary every 20 messages
        self.MAX_SUMMARY_LENGTH = 500  # Maximum summary length in words

    def create_summary(self, messages: List[Dict], existing_summary: str = None) -> str:
        """
        Create summary

        Args:
            messages: list of messages in format [{'role': 'user', 'content': '...'}, ...]
            existing_summary: previous summary (if exists)

        Returns:
            short dialog summary
        """
        self._logger.info(f"Creating summary from {len(messages)} messages...")

        dialog_text = self._format_messages_for_summary(messages)
        prompt = self._build_summary_prompt(dialog_text, existing_summary)

        # Генерируем резюме через LLM
        summary_messages = [
            {'role': 'system', 'content': summary_prompt},
            {'role': 'user', 'content': prompt}
        ]

        summary = self._llm.generate(summary_messages)

        self._logger.info(f"Summary created successful (length: {len(summary)} symbols)")

        return summary.strip()

    def _format_messages_for_summary(self, messages: List[Dict]) -> str:
        """Format messages for prompt"""
        formatted = []
        for msg in messages:
            role = "User" if msg['role'] == 'user' else "Assistant"
            formatted.append(f"{role}: {msg['content']}")

        return "\n".join(formatted)

    def _build_summary_prompt(self, dialog_text: str, existing_summary: str = None) -> str:
        """Build prompt for summarization"""

        if existing_summary:
            # Обновляем существующее резюме
            prompt = f"""У меня есть предыдущее резюме диалога и новые сообщения.

ПРЕДЫДУЩЕЕ РЕЗЮМЕ:
{existing_summary}

НОВЫЕ СООБЩЕНИЯ:
{dialog_text}

Требования к резюме:
1. Выдели ключевую информацию о пользователе (имя, работа, интересы)
2. Перечисли основные обсуждённые темы
3. Сохрани важные факты и детали
4. Будь лаконичным (максимум {self.MAX_SUMMARY_LENGTH} слов)

Дай ответ строго в следующем формате:

РЕЗЮМЕ ПОЛЬЗОВАТЕЛЯ
1. Информация 1: данные 1
2. Информация 2: данные 2
3. ...

Не пиши пользователю ничего, кроме резюме. Не задавай никаких вопросов."""
        else:
            # create new summary
            prompt = f"""Создай краткое резюме следующего диалога.

ДИАЛОГ:
{dialog_text}

Требования к резюме:
1. Выдели ключевую информацию о пользователе (имя, работа, интересы)
2. Перечисли основные обсуждённые темы
3. Сохрани важные факты и детали
4. Будь лаконичным (максимум {self.MAX_SUMMARY_LENGTH} слов)

Дай ответ строго в следующем формате:

РЕЗЮМЕ ПОЛЬЗОВАТЕЛЯ
1. Информация 1: данные 1
2. Информация 2: данные 2
3. ...

Не пиши пользователю ничего, кроме резюме. Не задавай никаких вопросов. 
"""

        return prompt

    def should_create_summary(self, message_count: int) -> bool:
        """
        Check neediness of summary creation

        Args:
            message_count: count of messages from latest summary

        Returns:
            True, if it's time to create summary
        """
        return message_count >= self.MESSAGES_PER_SUMMARY

    def create_incremental_summary(
            self,
            new_messages: List[Dict],
            existing_summary: str
    ) -> str:
        """
        Incremental summary update (adding a new information)

        Args:
            new_messages: new messages from latest summary
            existing_summary: current summary

        Returns:
            updated summary
        """
        return self.create_summary(new_messages, existing_summary)

    def extract_key_facts(self, summary: str) -> List[str]:
        """
        Extract key facts from summary
        (optional method for additional structurization)
        """
        prompt = f"""Из следующего резюме извлеки ключевые факты списком.

РЕЗЮМЕ:
{summary}

Формат ответа - простой список, каждый факт с новой строки:
- Факт 1
- Факт 2
...

КЛЮЧЕВЫЕ ФАКТЫ:"""

        messages = [
            {'role': 'system', 'content': 'Ты - ассистент, извлекающий факты.'},
            {'role': 'user', 'content': prompt}
        ]

        facts = self._llm.generate(messages)

        # break down into a list
        facts_list = [f.strip() for f in facts.split('\n') if f.strip()]

        return facts_list

# -*- coding: utf-8 -*-
"""
Инструменты долговременной памяти как вызываемые функции агента.

Позволяют агенту автономно сохранять важные факты о пользователе и проекте
в векторное хранилище (ChromaDB) и выполнять семантический поиск по
накопленным знаниям без участия пользователя. Зависимость от LongTermMemory
подключается через конструктор (duck typing), что изолирует модуль от
тяжёлых импортов и упрощает тестирование.
"""
from ai.agent.tool_base import Tool, ToolResult, ToolContext


class SaveMemoryTool(Tool):
    """Сохранение факта в долговременную память пользователя."""
    name = 'save_memory'
    description = (
        'Сохраняет важный факт, решение или предпочтение пользователя в долговременную '
        'память для использования в будущих диалогах. Вызывай, когда пользователь '
        'сообщает значимую информацию о себе, своём проекте или оборудовании '
        '(например: "запомни, что я использую STM32").')
    parameters = {
        'text': {'type': 'string', 'required': True,
                 'description': 'факт для сохранения в память, одна короткая фраза'},
    }

    def __init__(self, long_term_memory):
        self._memory = long_term_memory

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        if context is None or context.long_term_memory is None or not context.user_id:
            return ToolResult(success=False, error='Долговременная память недоступна в текущем контексте.')

        text = arguments['text'].strip()
        try:
            context.long_term_memory.save_fact(context.user_id, text)
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=f'Не удалось сохранить факт в память: {e}')

        return ToolResult(success=True, output=f'Сохранено в долговременную память: "{text}".')


class SearchMemoryTool(Tool):
    """Поиск релевантных фактов в долговременной памяти пользователя."""
    name = 'search_memory'
    description = (
        'Выполняет семантический поиск по долговременной памяти: находит сохранённые '
        'ранее факты и фрагменты диалогов, релевантные запросу. Вызывай, когда для '
        'ответа могут пригодиться сведения о прошлых проектах, оборудовании или '
        'предпочтениях пользователя.')
    parameters = {
        'query': {'type': 'string', 'required': True,
                  'description': 'поисковый запрос, например "какой микроконтроллер использует пользователь"'},
    }

    def __init__(self, long_term_memory):
        self._memory = long_term_memory

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        if context is None or context.long_term_memory is None or not context.user_id:
            return ToolResult(success=False, error='Долговременная память недоступна в текущем контексте.')

        query = arguments['query'].strip()
        try:
            facts = context.long_term_memory.search_facts(context.user_id, query, n_results=3)
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=f'Ошибка поиска в памяти: {e}')

        if not facts:
            return ToolResult(success=True, output='В долговременной памяти ничего не найдено по запросу.')

        listing = '\n'.join(f'{i}. {fact}' for i, fact in enumerate(facts, 1))
        return ToolResult(success=True, output=f'Найдено в долговременной памяти:\n{listing}')

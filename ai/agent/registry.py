# -*- coding: utf-8 -*-
"""
Реестр инструментов — программный узел маршрутизации агентной системы.

Языковая модель выбирает инструмент автономно по текстовым описаниям,
включаемым в системный промпт. Реестр сопоставляет имя из вызова
с зарегистрированным инструментом; при отсутствии инструмента
формируется сообщение об ошибке маршрутизации, которое возвращается
агенту для корректировки выбора (рефлексия).
"""
import logging

from ai.agent.tool_base import Tool
from logger.console import ConsoleLogger


class ToolRegistry:
    """Хранилище доступных инструментов и генератор их описаний для промпта."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._logger = ConsoleLogger(ToolRegistry.__name__, logging.INFO)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f'Инструмент с именем "{tool.name}" уже зарегистрирован.')
        self._tools[tool.name] = tool
        self._logger.debug(f'Tool registered: {tool.name}')

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def descriptions(self) -> str:
        """Сводное описание всех инструментов для системного промпта."""
        return '\n\n'.join(self._tools[name].describe() for name in sorted(self._tools))

    def __len__(self) -> int:
        return len(self._tools)

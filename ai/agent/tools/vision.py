# -*- coding: utf-8 -*-
"""
Инструмент анализа визуальной информации.

Реализует анализ изображений (схем, чертежей, диаграмм) как вызываемую
функцию агента: модель формулирует вопрос к изображению, инструмент
передаёт его Vision-Language модели вместе с последним изображением
пользователя и возвращает текстовое описание в контекст агента.
"""
from ai.agent.tool_base import Tool, ToolResult, ToolContext


class AnalyzeImageTool(Tool):
    """Анализ последнего изображения, отправленного пользователем."""
    name = 'analyze_image'
    description = (
        'Анализирует последнее изображение, отправленное пользователем (схему, чертёж, '
        'диаграмму), с помощью Vision-Language модели. Вызывай, когда для ответа нужно '
        'распознать компоненты на схеме, прочитать номиналы или описать изображение.')
    parameters = {
        'question': {'type': 'string', 'required': True,
                     'description': 'что требуется определить на изображении, например '
                                    '"какие компоненты изображены и каковы их номиналы"'},
    }

    def __init__(self, llm):
        self._llm = llm

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        uri = getattr(context, 'last_image_uri', None) if context is not None else None
        if not uri:
            return ToolResult(success=False, error=(
                'В текущем диалоге нет изображения. Попроси пользователя отправить '
                'схему или чертёж и ответь без инструмента.'))

        question = arguments['question'].strip()
        messages = [{
            'role': 'user',
            'content': [
                {'type': 'image_url', 'image_url': uri},
                {'type': 'text', 'text': question},
            ],
        }]

        try:
            answer = self._llm.generate(messages)
        except Exception as e:  # noqa: BLE001
            return ToolResult(success=False, error=f'Ошибка анализа изображения: {e}')

        return ToolResult(success=True, output=f'Анализ изображения:\n{answer}')

# -*- coding: utf-8 -*-
"""Тесты цикла агентного взаимодействия: вызовы инструментов, рефлексия, ограничитель итераций."""
import unittest

from ai.agent.loop import AgentLoop
from ai.agent.registry import ToolRegistry
from ai.agent.tool_base import Tool, ToolContext, ToolResult


class FakeLlm:
    """Модель-заглушка с заранее заданной последовательностью ответов."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.requests: list[list] = []

    def generate(self, messages) -> str:
        self.requests.append(messages)
        return self._responses.pop(0)


class EchoTool(Tool):
    name = 'echo'
    description = 'возвращает переданный текст'
    parameters = {'text': {'type': 'string', 'required': True, 'description': 'текст'}}

    def _execute(self, arguments, context) -> ToolResult:
        return ToolResult(success=True, output=f'эхо: {arguments["text"]}')


class BrokenTool(Tool):
    name = 'broken'
    description = 'всегда возвращает ошибку аргумента'
    parameters = {}

    def _execute(self, arguments, context) -> ToolResult:
        return ToolResult(success=False, error='недопустимое значение параметра')


class AgentLoopTest(unittest.TestCase):

    def test_tool_call_then_final_answer(self):
        llm = FakeLlm([
            '{"tool": "echo", "arguments": {"text": "привет"}}',
            'Окончательный ответ пользователю.',
        ])
        registry = ToolRegistry()
        registry.register(EchoTool())

        result = AgentLoop(llm, registry, max_iterations=5).run([{'role': 'user', 'content': 'вопрос'}])

        self.assertEqual(result.answer, 'Окончательный ответ пользователю.')
        self.assertEqual(result.iterations, 2)
        self.assertEqual(result.tool_calls, 1)
        self.assertEqual(result.errors, 0)
        self.assertEqual(result.stopped_reason, 'answer')
        self.assertEqual(len(result.steps), 1)

    def test_observation_is_added_to_context(self):
        llm = FakeLlm([
            '{"tool": "echo", "arguments": {"text": "данные"}}',
            'Ответ после наблюдения.',
        ])
        registry = ToolRegistry()
        registry.register(EchoTool())

        AgentLoop(llm, registry).run([{'role': 'user', 'content': 'вопрос'}])

        second_request = llm.requests[1]
        observation = second_request[-1]
        self.assertEqual(observation['role'], 'user')
        self.assertIn('[РЕЗУЛЬТАТ ВЫЗОВА ИНСТРУМЕНТА "echo"]', observation['content'])
        self.assertIn('эхо: данные', observation['content'])

    def test_unknown_tool_reflection(self):
        llm = FakeLlm([
            '{"tool": "nonexistent", "arguments": {}}',
            'Исправленный ответ.',
        ])
        registry = ToolRegistry()
        registry.register(EchoTool())

        result = AgentLoop(llm, registry).run([{'role': 'user', 'content': 'вопрос'}])

        self.assertEqual(result.answer, 'Исправленный ответ.')
        self.assertEqual(result.errors, 1)
        observation = llm.requests[1][-1]['content']
        self.assertIn('ОШИБКА МАРШРУТИЗАЦИИ', observation)
        self.assertIn('echo', observation)  # список доступных инструментов

    def test_error_reflection(self):
        llm = FakeLlm([
            '{"tool": "broken", "arguments": {}}',
            'Инструмент недоступен, отвечаю без него.',
        ])
        registry = ToolRegistry()
        registry.register(BrokenTool())

        result = AgentLoop(llm, registry).run([{'role': 'user', 'content': 'вопрос'}])

        self.assertEqual(result.errors, 1)
        observation = llm.requests[1][-1]['content']
        self.assertIn('[ОШИБКА ВЫЗОВА ИНСТРУМЕНТА "broken"]', observation)
        self.assertIn('недопустимое значение параметра', observation)
        self.assertIn('исправь аргументы', observation)

    def test_iteration_limit(self):
        # модель бесконечно вызывает инструмент - сработать должен ограничитель
        llm = FakeLlm([
            '{"tool": "echo", "arguments": {"text": "1"}}',
            '{"tool": "echo", "arguments": {"text": "2"}}',
            'Вынужденный окончательный ответ.',
        ])
        registry = ToolRegistry()
        registry.register(EchoTool())

        result = AgentLoop(llm, registry, max_iterations=2).run([{'role': 'user', 'content': 'вопрос'}])

        self.assertEqual(result.stopped_reason, 'limit')
        self.assertEqual(result.answer, 'Вынужденный окончательный ответ.')
        self.assertEqual(result.iterations, 3)  # 2 итерации цикла + принудительный ответ
        self.assertEqual(result.tool_calls, 2)

        forced_instruction = llm.requests[2][-1]['content']
        self.assertIn('НЕ вызывай инструменты', forced_instruction)

    def test_context_passed_to_tool(self):
        received = {}

        class ContextTool(Tool):
            name = 'ctx'
            description = 'контекст'
            parameters = {}

            def _execute(self, arguments, context):
                received['user_id'] = context.user_id if context else None
                return ToolResult(success=True, output='готово')

        llm = FakeLlm([
            '{"tool": "ctx", "arguments": {}}',
            'Ответ.',
        ])
        registry = ToolRegistry()
        registry.register(ContextTool())

        AgentLoop(llm, registry).run([{'role': 'user', 'content': 'вопрос'}], ToolContext(user_id=777))
        self.assertEqual(received['user_id'], 777)

    def test_metrics_elapsed_time(self):
        llm = FakeLlm(['Прямой ответ без инструментов.'])
        registry = ToolRegistry()

        result = AgentLoop(llm, registry).run([{'role': 'user', 'content': 'вопрос'}])

        self.assertEqual(result.iterations, 1)
        self.assertEqual(result.tool_calls, 0)
        self.assertGreaterEqual(result.elapsed_seconds, 0.0)
        self.assertIn('не вызывались', result.trace_text())

    def test_plain_answer_with_json_data_is_final(self):
        # ответ содержит JSON-данные, но без признаков вызова инструмента - это окончательный ответ
        llm = FakeLlm(['Результаты: {"voltage": 5, "current": 0.5} А.'])
        registry = ToolRegistry()
        registry.register(EchoTool())

        result = AgentLoop(llm, registry).run([{'role': 'user', 'content': 'вопрос'}])

        self.assertEqual(result.iterations, 1)
        self.assertEqual(result.tool_calls, 0)


if __name__ == '__main__':
    unittest.main()

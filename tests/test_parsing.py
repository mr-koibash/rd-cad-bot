# -*- coding: utf-8 -*-
"""Тесты парсера вызовов инструментов: типичные ошибки JSON-генерации локальной моделью."""
import unittest

from ai.agent.parsing import parse_tool_call


class ParseToolCallTest(unittest.TestCase):

    def test_plain_json(self):
        call = parse_tool_call('{"tool": "ohms_law", "arguments": {"voltage": 5, "resistance": 220}}')
        self.assertIsNotNone(call)
        self.assertEqual(call.name, 'ohms_law')
        self.assertEqual(call.arguments, {'voltage': 5, 'resistance': 220})

    def test_fenced_json(self):
        text = '```json\n{"tool": "led_resistor", "arguments": {"supply_voltage": 5}}\n```'
        call = parse_tool_call(text)
        self.assertIsNotNone(call)
        self.assertEqual(call.name, 'led_resistor')

    def test_json_with_text_around(self):
        text = 'Секунду, выполню расчёт. {"tool": "rc_filter", "arguments": {"resistance": 1000}} Готово.'
        call = parse_tool_call(text)
        self.assertIsNotNone(call)
        self.assertEqual(call.name, 'rc_filter')

    def test_trailing_comma(self):
        text = '{"tool": "ohms_law", "arguments": {"voltage": 5, "current": 0.02,}}'
        call = parse_tool_call(text)
        self.assertIsNotNone(call)
        self.assertEqual(call.arguments, {'voltage': 5, 'current': 0.02})

    def test_single_quotes(self):
        text = "{'tool': 'generate_gpio_code', 'arguments': {'port': 'A', 'pin': 5}}"
        call = parse_tool_call(text)
        self.assertIsNotNone(call)
        self.assertEqual(call.name, 'generate_gpio_code')
        self.assertEqual(call.arguments['port'], 'A')

    def test_arguments_as_string(self):
        text = '{"tool": "ohms_law", "arguments": "{\\"voltage\\": 12, \\"resistance\\": 4700}"}'
        call = parse_tool_call(text)
        self.assertIsNotNone(call)
        self.assertEqual(call.arguments, {'voltage': 12, 'resistance': 4700})

    def test_openai_style_function_field(self):
        text = '{"function": {"name": "led_resistor", "arguments": {"supply_voltage": 3.3}}}'
        call = parse_tool_call(text)
        self.assertIsNotNone(call)
        self.assertEqual(call.name, 'led_resistor')

    def test_name_key_variant(self):
        text = '{"name": "parallel_resistors", "parameters": {"resistances": [1000, 2000]}}'
        call = parse_tool_call(text)
        self.assertIsNotNone(call)
        self.assertEqual(call.name, 'parallel_resistors')
        self.assertEqual(call.arguments, {'resistances': [1000, 2000]})

    def test_plain_answer_returns_none(self):
        self.assertIsNone(parse_tool_call('Для питания схемы подойдёт линейный стабилизатор 7805.'))

    def test_json_without_tool_keys_returns_none(self):
        # JSON в ответе есть, но это данные, а не вызов инструмента
        self.assertIsNone(parse_tool_call('Вот параметры: {"voltage": 5, "current": 0.5}'))

    def test_nested_json(self):
        text = '{"tool": "save_memory", "arguments": {"text": "пользователь использует STM32F103"}}'
        call = parse_tool_call(text)
        self.assertIsNotNone(call)
        self.assertEqual(call.name, 'save_memory')

    def test_empty_arguments(self):
        text = '{"tool": "search_memory", "arguments": {}}'
        call = parse_tool_call(text)
        self.assertIsNotNone(call)
        self.assertEqual(call.arguments, {})


if __name__ == '__main__':
    unittest.main()

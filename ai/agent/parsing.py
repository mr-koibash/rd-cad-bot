# -*- coding: utf-8 -*-
"""
Разбор вызовов инструментов из текстового ответа языковой модели.

Локальные модели (в частности, Qwen) при формировании JSON-структур
допускают типичные ошибки: оборачивают объект в markdown-блоки ```json,
добавляют поясняющий текст до/после объекта, оставляют висячие запятые,
используют одинарные кавычки или передают аргументы строкой.

Модуль извлекает кандидатов JSON из ответа и поочерёдно пытается их
разобрать, исправляя перечисленные ошибки. Вызовом инструмента считается
только объект с полями "tool" (или "name"/"function") и "arguments" —
прочие JSON-объекты трактуются как обычный текст ответа.
"""
import json
import re

from ai.agent.tool_base import ToolCall


def parse_tool_call(text: str) -> ToolCall | None:
    """
    Извлекает вызов инструмента из ответа модели.

    Возвращает ToolCall, если найден JSON-объект с признаками вызова
    инструмента; иначе None — ответ считается окончательным текстом
    для пользователя.
    """
    if not text:
        return None

    for candidate in _extract_json_candidates(text):
        data = _try_loads(candidate)
        if not isinstance(data, dict):
            continue

        name = data.get('tool') or data.get('name') or data.get('function')
        if isinstance(name, dict):
            # стиль OpenAI: {"function": {"name": ..., "arguments": ...}}
            name = name.get('name')
        if not name or not isinstance(name, str):
            continue

        arguments = data.get('arguments', data.get('parameters', {}))
        if isinstance(arguments, str):
            arguments = _try_loads(arguments)
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            continue

        return ToolCall(name=name.strip(), arguments=arguments)

    return None


def _extract_json_candidates(text: str) -> list[str]:
    """Собирает строки-кандидаты JSON: блоки в бэктиках и сбалансированные {...}."""
    candidates: list[str] = []

    # 1. содержимое ```json ... ``` и ``` ... ```
    for match in re.findall(r'```(?:json)?\s*(.*?)```', text, flags=re.DOTALL | re.IGNORECASE):
        candidates.append(match.strip())

    # 2. сбалансированные по фигурным скобкам подстроки
    candidates.extend(_extract_balanced_objects(text))

    # сохраняем порядок появления, убираем дубликаты
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)

    return unique


def _extract_balanced_objects(text: str) -> list[str]:
    """Выделяет сбалансированные объекты {...} с учётом вложенности и строк."""
    objects: list[str] = []
    depth = 0
    start = -1
    in_string = False
    escape = False

    for i, char in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == '{':
            if depth == 0:
                start = i
            depth += 1
        elif char == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    objects.append(text[start:i + 1])
                    start = -1

    return objects


def _try_loads(candidate: str) -> dict | list | None:
    """Разбирает JSON-кандидат, исправляя типичные ошибки генерации."""
    cleaned = _cleanup(candidate)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    # висячие запятые перед } или ]
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    # «умные» кавычки вместо обычных
    cleaned = cleaned.replace('“', '"').replace('”', '"').replace('«', '"').replace('»', '"')
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    # одинарные кавычки — только если двойных нет вовсе
    if '"' not in cleaned:
        cleaned = cleaned.replace("'", '"')
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def _cleanup(candidate: str) -> str:
    """Базическая очистка: пробелы, markdown-обрамление, комментарии."""
    s = candidate.strip()
    if s.startswith('```'):
        s = re.sub(r'^```(?:json)?\s*', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s*```$', '', s)
    return s.strip()

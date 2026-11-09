# -*- coding: utf-8 -*-
"""
Программный цикл агентного взаимодействия.

Каждая итерация цикла:
    1. формирование рассуждения языковой моделью (генерация ответа);
    2. разбор ответа парсером вызовов инструментов;
    3. при наличии вызова - маршрутизация по реестру, исполнение кода
       инструмента и возвращение результата в контекст модели (наблюдение);
    4. при отсутствии вызова - цикл завершается, ответ считается окончательным.

Реализованные механизмы:
    - ограничитель количества итераций для предотвращения бесконечных циклов;
      при достижении лимита агенту направляется директива дать окончательный
      ответ без вызова инструментов;
    - простая рефлексия: при ошибке инструмента или ошибке маршрутизации
      агент получает уведомление с описанием ошибки и инструкцией
      скорректировать аргументы повторного вызова;
    - сбор метрик (число итераций, вызовы инструментов, ошибки, время)
      для анализа эффективности агентного режима.
"""
import logging
import time
from dataclasses import dataclass, field

from ai.agent.parsing import parse_tool_call
from ai.agent.registry import ToolRegistry
from ai.agent.tool_base import ToolContext
from logger.console import ConsoleLogger


@dataclass
class AgentStep:
    """Один шаг цикла: вызов инструмента и его результат."""
    iteration: int
    tool_name: str
    success: bool
    duration: float
    error: str = ''
    output_excerpt: str = ''


@dataclass
class AgentResult:
    """Итог работы агента: ответ и метрики."""
    answer: str
    steps: list[AgentStep] = field(default_factory=list)
    iterations: int = 0
    tool_calls: int = 0
    errors: int = 0
    elapsed_seconds: float = 0.0
    stopped_reason: str = 'answer'  # answer | limit

    def trace_text(self) -> str:
        """Компактная трассировка вызовов инструментов (для отладки/демонстрации)."""
        if not self.steps:
            return 'Инструменты не вызывались.'
        lines = []
        for step in self.steps:
            status = 'OK' if step.success else f'ОШИБКА: {step.error}'
            lines.append(f'{step.iteration}. {step.tool_name} ({step.duration:.2f} c) - {status}')
        lines.append(
            f'Итого: итераций {self.iterations}, вызовов {self.tool_calls}, '
            f'ошибок {self.errors}, время {self.elapsed_seconds:.2f} c, '
            f'остановка: {self.stopped_reason}')
        return '\n'.join(lines)


# Директива при исчерпании лимита итераций
_FORCED_ANSWER_INSTRUCTION = (
    'Достигнут лимит итераций. Больше НЕ вызывай инструменты. '
    'Дай окончательный ответ пользователю на основе имеющейся информации прямо сейчас.'
)


class AgentLoop:
    """Цикл агентного взаимодействия: рассуждение -> вызов инструмента -> результат."""

    def __init__(self, llm, registry: ToolRegistry, max_iterations: int = 5):
        self._llm = llm
        self._registry = registry
        self._max_iterations = max(1, int(max_iterations))
        self._logger = ConsoleLogger(AgentLoop.__name__, logging.INFO)

    def run(self, messages: list, context: ToolContext | None = None) -> AgentResult:
        started = time.monotonic()
        working: list[dict] = [dict(message) for message in messages]

        steps: list[AgentStep] = []
        iterations = 0
        tool_calls = 0
        errors = 0
        answer = ''

        for iteration in range(1, self._max_iterations + 1):
            raw_response = self._llm.generate(working)
            iterations += 1

            call = parse_tool_call(raw_response)
            if call is None:
                # вызова инструмента нет - окончательный ответ
                answer = raw_response.strip()
                return AgentResult(
                    answer=answer, steps=steps, iterations=iterations, tool_calls=tool_calls,
                    errors=errors, elapsed_seconds=time.monotonic() - started, stopped_reason='answer')

            observation, step = self._invoke_tool(call, iteration, context)
            steps.append(step)
            if step.success:
                tool_calls += 1
            else:
                tool_calls += 1
                errors += 1

            self._logger.debug(
                f'Iteration {iteration}: tool={step.tool_name}, success={step.success}, {step.duration:.2f}s')

            working.append({'role': 'assistant', 'content': raw_response})
            working.append({'role': 'user', 'content': observation})

        # лимит итераций исчерпан - запрашиваем окончательный ответ
        iterations += 1
        working.append({'role': 'user', 'content': _FORCED_ANSWER_INSTRUCTION})
        answer = self._llm.generate(working).strip()

        return AgentResult(
            answer=answer, steps=steps, iterations=iterations, tool_calls=tool_calls,
            errors=errors, elapsed_seconds=time.monotonic() - started, stopped_reason='limit')

    def _invoke_tool(self, call, iteration: int, context: ToolContext | None):
        """Маршрутизация вызова, исполнение инструмента и формирование наблюдения (рефлексия)."""
        step_started = time.monotonic()

        tool = self._registry.get(call.name)
        if tool is None:
            observation = (
                f'[ОШИБКА МАРШРУТИЗАЦИИ]\n'
                f'Инструмент "{call.name}" не найден. '
                f'Доступные инструменты: {", ".join(self._registry.names())}.\n'
                f'Выбери подходящий инструмент из списка и повтори вызов в том же JSON-формате.')
            return observation, AgentStep(
                iteration=iteration, tool_name=call.name, success=False,
                duration=time.monotonic() - step_started,
                error='инструмент не найден')

        result = tool.run(call.arguments, context)
        duration = time.monotonic() - step_started

        if result.success:
            observation = (
                f'[РЕЗУЛЬТАТ ВЫЗОВА ИНСТРУМЕНТА "{call.name}"]\n'
                f'{result.output}\n\n'
                f'Продолжай решать задачу: при необходимости вызови следующий инструмент или дай окончательный ответ '
                f'пользователю обычным текстом (без JSON). Числа, единицы измерения и код из результата приведи в '
                f'ответе полностью и без изменений.')
        else:
            observation = (
                f'[ОШИБКА ВЫЗОВА ИНСТРУМЕНТА "{call.name}"]\n'
                f'{result.error}\n\n'
                f'Проверь имена и типы параметров, исправь аргументы и вызови инструмент повторно. '
                f'Не повторяй вызов с теми же аргументами.')

        return observation, AgentStep(
            iteration=iteration, tool_name=call.name, success=result.success,
            duration=duration, error=result.error,
            output_excerpt=result.output[:200])

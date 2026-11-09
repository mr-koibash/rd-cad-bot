# -*- coding: utf-8 -*-
"""
Базовые абстракции инструментария ИИ-агента.

Инструмент (Tool) — программная функция, которую языковая модель может вызвать
в ходе решения задачи. Модель выбирает инструмент по текстовому описанию
(маршрутизация), формирует аргументы в виде JSON, а результат выполнения
возвращается в контекст диалога как наблюдение.

Базовый класс Tool выполняет валидацию и приведение типов аргументов,
проверяя их соответствие объявленной схеме parameters. Ошибки валидации
возвращаются как ToolResult с success=False — это основа механизма
рефлексии: агент получает текст ошибки и корректирует повторный вызов.
"""
from dataclasses import dataclass, field
from typing import Any


class ToolArgumentError(Exception):
    """Ошибка в аргументах вызова инструмента (для передачи модели в рефлексии)."""


@dataclass
class ToolResult:
    """Результат выполнения инструмента."""
    success: bool
    output: str = ''
    error: str = ''


@dataclass
class ToolCall:
    """Разобранный вызов инструмента, извлечённый из ответа модели."""
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass
class ToolContext:
    """Контекст выполнения инструмента: данные текущего диалога и сервисы."""
    user_id: int | None = None
    last_image_uri: str | None = None
    long_term_memory: Any = None  # LongTermMemory (duck typing, без жёсткой зависимости)


# Множители инженерной записи чисел: "4.7k" -> 4700, "100n" -> 1e-7 и т.п.
# Порядок важен: "мк" должно проверяться раньше "м", "Мег" — раньше "М".
_MULTIPLIERS: list[tuple[str, float]] = [
    ('мег', 1e6), ('meg', 1e6),
    ('мк', 1e-6), ('µ', 1e-6), ('μ', 1e-6), ('u', 1e-6),
    ('н', 1e-9), ('n', 1e-9),
    ('п', 1e-12), ('p', 1e-12),
    ('к', 1e3), ('k', 1e3), ('K', 1e3),
    ('М', 1e6), ('M', 1e6),
    ('м', 1e-3), ('m', 1e-3),
    ('Г', 1e9), ('G', 1e9),
]

# Единицы измерения, отбрасываемые при разборе ("10кОм" -> "10к")
_UNITS = (
    'Ом', 'ом', 'Ohm', 'ohm', 'OHM',
    'Ф', 'ф', 'F',
    'В', 'в', 'V',
    'А', 'а',
    'Гц', 'гц', 'Hz', 'hz', 'HZ',
    'с', 's',
)


def parse_value(value: Any, param_name: str = 'значение') -> float:
    """
    Преобразует аргумент в число. Помимо обычных чисел поддерживает
    инженерную запись строк: "4.7к", "100n", "2,2 кОм".
    """
    if isinstance(value, bool):
        raise ToolArgumentError(f'Параметр "{param_name}" должен быть числом, получено логическое значение.')
    if isinstance(value, (int, float)):
        return float(value)

    if not isinstance(value, str):
        raise ToolArgumentError(f'Параметр "{param_name}" должен быть числом.')

    s = value.strip().replace(',', '.').replace(' ', '')
    if not s:
        raise ToolArgumentError(f'Параметр "{param_name}" пуст.')

    try:
        return float(s)
    except ValueError:
        pass

    # отбрасываем единицы измерения (длинные — первыми)
    changed = True
    while changed and s:
        changed = False
        for unit in sorted(set(_UNITS), key=len, reverse=True):
            if s.endswith(unit):
                s = s[:-len(unit)]
                changed = True
                break

    import re
    match = re.fullmatch(r'([-+]?\d*\.?\d+)([a-zA-Zа-яА-Яµμ]*)', s)
    if match is None:
        raise ToolArgumentError(
            f'Не удалось преобразовать "{value}" в число. '
            'Используй число или инженерную запись, например: 4700, "4.7k", "100n".')

    number = float(match.group(1))
    suffix = match.group(2)
    if not suffix:
        return number

    for prefix, scale in _MULTIPLIERS:
        if suffix == prefix:
            return number * scale

    raise ToolArgumentError(
        f'Неизвестный множитель "{suffix}" в значении "{value}". '
        'Допустимо: п(p), н(n), мк(u/µ), м(m), к(k), М(M), Г(G).')


def format_number(value: float) -> str:
    """Компактное отображение числа без лишних нулей."""
    return f'{value:.6g}'


class Tool:
    """
    Базовый класс инструмента агента.

    Наследник определяет:
      - name        — короткое имя для вызова из JSON;
      - description — описание для маршрутизации (что и когда применять);
      - parameters  — схема параметров вида
            {'имя': {'type': 'value'|'number'|'integer'|'string'|'array',
                     'description': '...', 'required': True/False,
                     'enum': [...], 'items_type': 'value'}}
      - _execute(arguments, context) -> ToolResult — полезная нагрузка.
    """

    name: str = 'base_tool'
    description: str = ''
    parameters: dict = {}

    def run(self, arguments: dict | None, context: ToolContext | None = None) -> ToolResult:
        """Валидирует аргументы и выполняет инструмент."""
        try:
            prepared = self._validate_arguments(arguments or {})
        except ToolArgumentError as e:
            return ToolResult(success=False, error=str(e))

        try:
            return self._execute(prepared, context)
        except ToolArgumentError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:  # noqa: BLE001 — ошибка уходит в рефлексию агента
            return ToolResult(success=False, error=f'Внутренняя ошибка инструмента: {e}')

    def _validate_arguments(self, arguments: dict) -> dict:
        prepared = {}
        for param_name, spec in self.parameters.items():
            value = arguments.get(param_name)
            if value is None:
                if spec.get('required', False):
                    raise ToolArgumentError(
                        f'Отсутствует обязательный параметр "{param_name}" — {spec.get("description", "")}'.strip())
                continue
            prepared[param_name] = self._coerce(value, spec.get('type', 'string'), param_name, spec)
        return prepared

    def _coerce(self, value, expected_type: str, param_name: str, spec: dict):
        if expected_type in ('number', 'value'):
            parsed = parse_value(value, param_name)
            if 'enum' in spec and parsed not in spec['enum']:
                allowed = ', '.join(str(v) for v in spec['enum'])
                raise ToolArgumentError(f'Параметр "{param_name}" должен быть одним из: {allowed}.')
            return parsed

        if expected_type == 'integer':
            parsed = parse_value(value, param_name)
            return int(round(parsed))

        if expected_type == 'string':
            text = str(value).strip()
            if 'enum' in spec and text not in spec['enum']:
                allowed = ', '.join(str(v) for v in spec['enum'])
                raise ToolArgumentError(f'Параметр "{param_name}" должен быть одним из: {allowed}.')
            if not text:
                raise ToolArgumentError(f'Параметр "{param_name}" не может быть пустым.')
            return text

        if expected_type == 'array':
            if not isinstance(value, list) or not value:
                raise ToolArgumentError(
                    f'Параметр "{param_name}" должен быть непустым массивом, например: [1000, 4700, 330].')
            items_type = spec.get('items_type', 'string')
            if items_type == 'value':
                return [parse_value(item, param_name) for item in value]
            return [str(item) for item in value]

        return value

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:  # pragma: no cover
        raise NotImplementedError

    def describe(self) -> str:
        """Текстовое описание инструмента для системного промпта (узел маршрутизации)."""
        lines = [f'### {self.name}', self.description]
        if self.parameters:
            lines.append('Параметры:')
            for param_name, spec in self.parameters.items():
                required = 'обязателен' if spec.get('required', False) else 'необязателен'
                enum = f". Допустимые значения: {', '.join(str(v) for v in spec['enum'])}" if 'enum' in spec else ''
                lines.append(
                    f'- {param_name} ({spec.get("type", "string")}, {required}): {spec.get("description", "")}{enum}')
        return '\n'.join(lines)

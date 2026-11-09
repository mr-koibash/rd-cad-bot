# -*- coding: utf-8 -*-
"""
Инструменты расчёта параметров электронных компонентов.

Делегирование математических вычислений внешним программным модулям
устраняет арифметические галлюцинации языковой модели: все значения
вычисляются детерминированным кодом и возвращаются агенту в готовом виде
вместе с использованными формулами.

Поддерживается инженерная запись величин во входных аргументах:
"4.7k" = 4700 Ом, "100n" = 100 нФ, "2,2 кОм" = 2200 Ом и т.п.
"""
import math

from ai.agent.tool_base import Tool, ToolResult, ToolContext, format_number

# Базовый ряд E24 для подбора ближайшего стандартного номинала резистора
_E24_BASE = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7,
             3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]


def nearest_e24(value: float) -> float | None:
    """Ближайший стандартный номинал ряда E24 (по логарифмической близости)."""
    if value <= 0:
        return None
    decade = math.floor(math.log10(value))
    candidates = [base * 10 ** d for d in (decade - 1, decade, decade + 1) for base in _E24_BASE]
    return min(candidates, key=lambda c: abs(math.log(c / value)))


class OhmsLawTool(Tool):
    """Расчёт по закону Ома: по любым двум величинам определяет третью и мощность."""
    name = 'ohms_law'
    description = (
        'Расчёт электрической цепи по закону Ома. Передай ЛЮБЫЕ ДВЕ из трёх величин '
        '(voltage, current, resistance) - инструмент вычислит третью, а также мощность. '
        'Используй для любого вопроса про ток, напряжение или сопротивление.')
    parameters = {
        'voltage': {'type': 'value', 'required': False,
                    'description': 'напряжение в вольтах (В), например 5 или 12'},
        'current': {'type': 'value', 'required': False,
                    'description': 'ток в амперах (А), например 0.02 для 20 мА'},
        'resistance': {'type': 'value', 'required': False,
                       'description': 'сопротивление в омах (Ом), например 220 или "4.7k"'},
    }

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        u = arguments.get('voltage')
        i = arguments.get('current')
        r = arguments.get('resistance')

        provided = sum(x is not None for x in (u, i, r))
        if provided < 2:
            return ToolResult(success=False, error=(
                'Для расчёта необходимы ровно две известные величины из трёх '
                '(voltage, current, resistance). Передано известных величин: '
                f'{provided}. Повтори вызов с двумя аргументами.'))

        if u is None:
            u = i * r
            formula = 'U = I * R'
        elif i is None:
            if r == 0:
                return ToolResult(success=False, error='Сопротивление не может быть равно нулю при расчёте тока.')
            i = u / r
            formula = 'I = U / R'
        else:
            if i == 0:
                return ToolResult(success=False, error='Ток не может быть равен нулю при расчёте сопротивления.')
            r = u / i
            formula = 'R = U / I'

        p = u * i
        output = (
            f'Расчёт по закону Ома ({formula}):\n'
            f'- напряжение U = {format_number(u)} В\n'
            f'- ток I = {format_number(i)} А ({format_number(i * 1000)} мА)\n'
            f'- сопротивление R = {format_number(r)} Ом\n'
            f'- мощность P = U * I = {format_number(p)} Вт\n'
            f'Рекомендуемая мощность резистора с запасом: от {format_number(p * 2)} Вт.')
        return ToolResult(success=True, output=output)


class LedResistorTool(Tool):
    """Расчёт токоограничивающего резистора для светодиода."""
    name = 'led_resistor'
    description = (
        'Расчёт токоограничивающего резистора для светодиода: по напряжению питания, '
        'прямому напряжению и току светодиода вычисляет сопротивление, мощность и '
        'ближайший стандартный номинал ряда E24.')
    parameters = {
        'supply_voltage': {'type': 'value', 'required': True,
                           'description': 'напряжение питания в вольтах (В), например 5'},
        'led_voltage': {'type': 'value', 'required': True,
                        'description': 'прямое падение напряжения на светодиоде в вольтах (В), обычно 1.8-3.5'},
        'led_current': {'type': 'value', 'required': True,
                        'description': 'номинальный ток светодиода в амперах (А), например 0.02 для 20 мА'},
    }

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        us = arguments['supply_voltage']
        uled = arguments['led_voltage']
        current = arguments['led_current']

        if current <= 0:
            return ToolResult(success=False, error='Ток светодиода должен быть положительным.')
        if us <= uled:
            return ToolResult(success=False, error=(
                f'Напряжение питания ({format_number(us)} В) должно быть больше '
                f'падения напряжения на светодиоде ({format_number(uled)} В).'))

        resistance = (us - uled) / current
        power = (us - uled) * current
        e24 = nearest_e24(resistance)

        output = (
            f'Расчёт резистора для светодиода:\n'
            f'- формула: R = (Uпит - Uled) / Iled\n'
            f'- R = ({format_number(us)} - {format_number(uled)}) / {format_number(current)} = '
            f'{format_number(resistance)} Ом\n'
            f'- мощность на резисторе: P = {format_number(power)} Вт (выбирай резистор от '
            f'{format_number(power * 2)} Вт)\n'
            f'- ближайший номинал E24: {format_number(e24)} Ом')
        return ToolResult(success=True, output=output)


class VoltageDividerTool(Tool):
    """Расчёт выходного напряжения резистивного делителя."""
    name = 'voltage_divider'
    description = (
        'Расчёт резистивного делителя напряжения: по входному напряжению и двум '
        'сопротивлениям вычисляет выходное напряжение, ток и мощность делителя.')
    parameters = {
        'input_voltage': {'type': 'value', 'required': True,
                          'description': 'входное напряжение делителя в вольтах (В)'},
        'r1': {'type': 'value', 'required': True,
               'description': 'сопротивление верхнего (подключённого к входу) резистора, Ом'},
        'r2': {'type': 'value', 'required': True,
               'description': 'сопротивление нижнего (подключённого к земле) резистора, Ом'},
    }

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        vin = arguments['input_voltage']
        r1 = arguments['r1']
        r2 = arguments['r2']

        if r1 <= 0 or r2 <= 0:
            return ToolResult(success=False, error='Сопротивления делителя должны быть положительными.')

        vout = vin * r2 / (r1 + r2)
        current = vin / (r1 + r2)
        p1 = current ** 2 * r1
        p2 = current ** 2 * r2

        output = (
            f'Расчёт делителя напряжения:\n'
            f'- Uвых = Uвх * R2 / (R1 + R2) = {format_number(vin)} * {format_number(r2)} / '
            f'({format_number(r1)} + {format_number(r2)}) = {format_number(vout)} В\n'
            f'- ток через делитель: I = {format_number(current)} А ({format_number(current * 1000)} мА)\n'
            f'- мощность: P(R1) = {format_number(p1)} Вт, P(R2) = {format_number(p2)} Вт')
        return ToolResult(success=True, output=output)


class RcFilterTool(Tool):
    """Расчёт постоянной времени и частоты среза RC-цепи."""
    name = 'rc_filter'
    description = (
        'Расчёт RC-цепи: по сопротивлению и ёмкости вычисляет постоянную времени '
        'и частоту среза ФНЧ (фильтра нижних частот).')
    parameters = {
        'resistance': {'type': 'value', 'required': True,
                       'description': 'сопротивление резистора в омах (Ом), например 1000 или "1k"'},
        'capacitance': {'type': 'value', 'required': True,
                        'description': 'ёмкость конденсатора в фарадах (Ф), например 0.0000001, "100n" или "100н"'},
    }

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        r = arguments['resistance']
        c = arguments['capacitance']

        if r <= 0 or c <= 0:
            return ToolResult(success=False, error='Сопротивление и ёмкость должны быть положительными.')

        tau = r * c
        cutoff = 1 / (2 * math.pi * r * c)

        output = (
            f'Расчёт RC-цепи:\n'
            f'- постоянная времени: tau = R * C = {format_number(r)} * {format_number(c)} = '
            f'{format_number(tau)} с\n'
            f'- частота среза ФНЧ: f = 1 / (2 * pi * R * C) = {format_number(cutoff)} Гц')
        return ToolResult(success=True, output=output)


class ParallelResistorsTool(Tool):
    """Расчёт эквивалентного сопротивления параллельно соединённых резисторов."""
    name = 'parallel_resistors'
    description = (
        'Расчёт эквивалентного сопротивления при параллельном соединении резисторов. '
        'Передай массив номиналов в омах.')
    parameters = {
        'resistances': {'type': 'array', 'required': True, 'items_type': 'value',
                        'description': 'массив сопротивлений в омах, например [1000, 4700, 330]'},
    }

    def _execute(self, arguments: dict, context: ToolContext | None) -> ToolResult:
        resistances = arguments['resistances']

        if any(r <= 0 for r in resistances):
            return ToolResult(success=False, error='Все сопротивления должны быть положительными.')

        equivalent = 1 / sum(1 / r for r in resistances)
        listing = ', '.join(format_number(r) for r in resistances)

        output = (
            f'Расчёт параллельного соединения резисторов:\n'
            f'- номиналы: {listing} Ом\n'
            f'- формула: 1/Rэкв = 1/R1 + 1/R2 + ... + 1/Rn\n'
            f'- Rэкв = {format_number(equivalent)} Ом')
        return ToolResult(success=True, output=output)

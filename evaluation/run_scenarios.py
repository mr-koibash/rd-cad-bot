# -*- coding: utf-8 -*-
"""
Тестирование агентной системы на типовых инженерных сценариях.

Формирует многошаговые инженерные запросы, выполняет их через агентный
цикл и фиксирует метрики: успешность, использованные инструменты, число
итераций и время ответа. Поддерживаются два режима:

    python evaluation/run_scenarios.py                # активный ИИ-агент
    python evaluation/run_scenarios.py --mode assistant  # пассивный ассистент (для сравнения)

Запускать на машине с настроенным окружением (см. README): модели Qwen,
llama.cpp, при наличии - chromadb для инструментов памяти. База данных
и Telegram не требуются: сценарии выполняются напрямую через AgentLoop.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Метрики ожидания для каждого сценария
SCENARIOS = [
    {
        'id': 1,
        'question': 'Рассчитай номинал токоограничивающего резистора для светодиода: '
                    'напряжение питания 5 В, падение на светодиоде 2 В, ток 20 мА.',
        'expect_contains': '150',
        'expect_tool': 'led_resistor',
    },
    {
        'id': 2,
        'question': 'Какое напряжение будет на выходе резистивного делителя, если вход 12 В, '
                    'верхнее плечо 10 кОм, нижнее 4,7 кОм?',
        'expect_contains': '3.8',
        'expect_tool': 'voltage_divider',
    },
    {
        'id': 3,
        'question': 'Какой ток протекает через резистор 220 Ом при напряжении 5 В '
                    'и какая мощность на нём рассеивается?',
        'expect_contains': '0.0227',
        'expect_tool': 'ohms_law',
    },
    {
        'id': 4,
        'question': 'Определи частоту среза RC-фильтра нижних частот с резистором 1 кОм '
                    'и конденсатором 100 нФ.',
        'expect_contains': '1591',
        'expect_tool': 'rc_filter',
    },
    {
        'id': 5,
        'question': 'Чему равно эквивалентное сопротивление трёх параллельно соединённых '
                    'резисторов: 1 кОм, 2 кОм и 3 кОм?',
        'expect_contains': '545',
        'expect_tool': 'parallel_resistors',
    },
    {
        'id': 6,
        'question': 'Сгенерируй код инициализации UART1 со скоростью 115200 бит/с для STM32.',
        'expect_contains': '115200',
        'expect_tool': 'generate_uart_code',
    },
    {
        'id': 7,
        'question': 'Сгенерируй код инициализации вывода PA5 как выхода для управления светодиодом.',
        'expect_contains': 'GPIO_PIN_5',
        'expect_tool': 'generate_gpio_code',
    },
    {
        'id': 8,
        'question': 'Запомни, пожалуйста: в моём проекте используется микроконтроллер STM32F103C8T6.',
        'expect_contains': 'сохран',
        'expect_tool': 'save_memory',
    },
]

EVALUATION_USER_ID = 999999


def build_agent(config_path: str):
    """Собирает агентный цикл с реальной моделью (без Telegram и БД)."""
    from configparser import ConfigParser

    from ai.agent.loop import AgentLoop
    from ai.agent.registry import ToolRegistry
    from ai.agent.prompts import build_agent_system_prompt
    from ai.agent.tools import create_default_tools
    from ai.llm import Llm
    from services.service_locator import ServiceLocator

    config = ConfigParser()
    config.read(config_path)
    service_locator = ServiceLocator()
    service_locator.add(ConfigParser.__name__, config)

    llm = Llm(service_locator)

    long_term_memory = None
    try:
        from ai.long_term_memory import LongTermMemory
        long_term_memory = LongTermMemory(db_path=config['LongTermMemory']['chroma_directory'])
    except Exception as e:
        print(f'[i] Долговременная память недоступна ({e}) - сценарий 8 будет пропущен')

    tool_registry = ToolRegistry()
    for tool in create_default_tools(long_term_memory=long_term_memory, llm=llm):
        tool_registry.register(tool)

    agent = AgentLoop(llm, tool_registry, max_iterations=int(config['Agent']['max_iterations']))
    return agent, build_agent_system_prompt(tool_registry.descriptions()), llm


def run_agent_scenarios(agent, system_prompt):
    from ai.agent.tool_base import ToolContext

    results = []
    for scenario in SCENARIOS:
        if scenario['expect_tool'] == 'save_memory' and len(agent._registry) < 10:
            print(f"Сценарий {scenario['id']}: пропущен (нет инструментов памяти)")
            continue

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': scenario['question']},
        ]
        context = ToolContext(user_id=EVALUATION_USER_ID)

        print(f"Сценарий {scenario['id']}: {scenario['question'][:60]}...")
        agent_result = agent.run(messages, context)

        expected = scenario['expect_contains']
        success = expected in agent_result.answer
        tools_used = [step.tool_name for step in agent_result.steps]

        results.append({
            'id': scenario['id'],
            'success': success,
            'tools': tools_used,
            'iterations': agent_result.iterations,
            'errors': agent_result.errors,
            'time': agent_result.elapsed_seconds,
            'answer_excerpt': agent_result.answer[:150].replace('\n', ' '),
        })
        print(f"  -> {'УСПЕХ' if success else 'ПРОВАЛ'} | итерации: {agent_result.iterations}, "
              f"инструменты: {tools_used}, время: {agent_result.elapsed_seconds:.2f} c")

    return results


def run_assistant_scenarios(llm):
    """Пассивный режим: те же вопросы без инструментов (для сравнительного анализа)."""
    from ai.prompts import cad_prompt

    results = []
    for scenario in SCENARIOS:
        if scenario['expect_tool'] == 'save_memory':
            continue

        messages = [
            {'role': 'system', 'content': cad_prompt},
            {'role': 'user', 'content': scenario['question']},
        ]

        print(f"Сценарий {scenario['id']}: {scenario['question'][:60]}...")
        started = time.monotonic()
        answer = llm.generate(messages).strip()
        elapsed = time.monotonic() - started

        expected = scenario['expect_contains']
        success = expected in answer

        results.append({
            'id': scenario['id'],
            'success': success,
            'tools': [],
            'iterations': 1,
            'errors': 0,
            'time': elapsed,
            'answer_excerpt': answer[:150].replace('\n', ' '),
        })
        print(f"  -> {'УСПЕХ' if success else 'ПРОВАЛ'} | время: {elapsed:.2f} c")

    return results


def print_report(mode: str, results: list):
    total = len(results)
    if total == 0:
        print('Нет результатов.')
        return

    successful = sum(1 for r in results if r['success'])
    avg_iterations = sum(r['iterations'] for r in results) / total
    avg_time = sum(r['time'] for r in results) / total
    total_errors = sum(r['errors'] for r in results)

    print('\n' + '=' * 70)
    print(f'ИТОГИ ТЕСТИРОВАНИЯ (режим: {"активный ИИ-агент" if mode == "agent" else "пассивный ассистент"})')
    print('=' * 70)
    print(f'{"ID":<4}{"Успех":<8}{"Итерации":<10}{"Ошибки":<8}{"Время, с":<10}Инструменты')
    for r in results:
        print(f"{r['id']:<4}{'ДА' if r['success'] else 'НЕТ':<8}{r['iterations']:<10}{r['errors']:<8}"
              f"{r['time']:<10.2f}{', '.join(r['tools']) or '-'}")
    print('-' * 70)
    print(f'Процент успешных операций: {successful / total * 100:.0f}% ({successful} из {total})')
    print(f'Среднее количество итераций: {avg_iterations:.2f}')
    print(f'Среднее время ответа: {avg_time:.2f} с')
    print(f'Суммарное количество ошибок инструментов: {total_errors}')
    print('=' * 70)


def main():
    parser = argparse.ArgumentParser(description='Тестирование агентной системы на инженерных сценариях')
    parser.add_argument('--mode', choices=['agent', 'assistant'], default='agent',
                        help='режим работы: agent (с инструментами) или assistant (без инструментов)')
    parser.add_argument('--config', default=str(Path(__file__).resolve().parent.parent / 'config.ini'),
                        help='путь к config.ini')
    args = parser.parse_args()

    agent, system_prompt, llm = build_agent(args.config)

    if args.mode == 'agent':
        results = run_agent_scenarios(agent, system_prompt)
    else:
        results = run_assistant_scenarios(llm)

    print_report(args.mode, results)


if __name__ == '__main__':
    main()

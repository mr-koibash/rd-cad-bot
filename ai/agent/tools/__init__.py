# -*- coding: utf-8 -*-
"""
Набор инструментов ИИ-агента и фабрика для их регистрации.

create_default_tools собирает базовый набор инструментов агентной системы:
расчёт электронных компонентов, генерация кода периферии микроконтроллеров,
а также (при наличии зависимостей) инструменты долговременной памяти
и анализа визуальной информации.
"""
from ai.agent.tools.electronics import (
    LedResistorTool,
    OhmsLawTool,
    ParallelResistorsTool,
    RcFilterTool,
    VoltageDividerTool,
)
from ai.agent.tools.mcu_codegen import GpioCodeTool, I2cCodeTool, SpiCodeTool, UartCodeTool


def create_default_tools(long_term_memory=None, llm=None) -> list:
    """Создаёт базовый набор инструментов агента.

    Инструменты памяти регистрируются при переданном LongTermMemory,
    инструмент анализа изображений - при переданной LLM.
    """
    tools = [
        OhmsLawTool(),
        LedResistorTool(),
        VoltageDividerTool(),
        RcFilterTool(),
        ParallelResistorsTool(),
        GpioCodeTool(),
        UartCodeTool(),
        SpiCodeTool(),
        I2cCodeTool(),
    ]

    if long_term_memory is not None:
        from ai.agent.tools.memory_tools import SaveMemoryTool, SearchMemoryTool
        tools.extend([SaveMemoryTool(long_term_memory), SearchMemoryTool(long_term_memory)])

    if llm is not None:
        from ai.agent.tools.vision import AnalyzeImageTool
        tools.append(AnalyzeImageTool(llm))

    return tools

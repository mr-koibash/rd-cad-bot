# -*- coding: utf-8 -*-
"""Тесты инженерных инструментов: расчёты, валидация аргументов, генерация кода."""
import unittest

from ai.agent.registry import ToolRegistry
from ai.agent.tool_base import Tool, ToolContext, parse_value
from ai.agent.tools.electronics import (
    LedResistorTool,
    OhmsLawTool,
    ParallelResistorsTool,
    RcFilterTool,
    VoltageDividerTool,
)
from ai.agent.tools.mcu_codegen import GpioCodeTool, I2cCodeTool, SpiCodeTool, UartCodeTool


class ValueParsingTest(unittest.TestCase):

    def test_plain_numbers(self):
        self.assertEqual(parse_value(220), 220.0)
        self.assertEqual(parse_value('4700'), 4700.0)

    def test_engineering_suffixes(self):
        self.assertEqual(parse_value('4.7k'), 4700.0)
        self.assertEqual(parse_value('4,7к'), 4700.0)
        self.assertAlmostEqual(parse_value('100n'), 1e-7)
        self.assertAlmostEqual(parse_value('100н'), 1e-7)
        self.assertEqual(parse_value('10кОм'), 10000.0)
        self.assertAlmostEqual(parse_value('2.2 МОм'), 2.2e6)
        self.assertAlmostEqual(parse_value('10u'), 1e-5)
        self.assertAlmostEqual(parse_value('10мк'), 1e-5)

    def test_invalid_value(self):
        from ai.agent.tool_base import ToolArgumentError
        with self.assertRaises(ToolArgumentError):
            parse_value('abc')


class OhmsLawTest(unittest.TestCase):

    def setUp(self):
        self.tool = OhmsLawTool()

    def test_compute_current(self):
        result = self.tool.run({'voltage': 5, 'resistance': 220})
        self.assertTrue(result.success)
        self.assertIn('0.0227273', result.output)  # I = 5/220
        self.assertIn('0.113636', result.output)  # P = U*I

    def test_compute_resistance(self):
        result = self.tool.run({'voltage': 5, 'current': 0.02})
        self.assertTrue(result.success)
        self.assertIn('250', result.output)  # R = 5/0.02

    def test_compute_voltage(self):
        result = self.tool.run({'current': 0.01, 'resistance': 470})
        self.assertTrue(result.success)
        self.assertIn('4.7', result.output)

    def test_engineering_notation(self):
        result = self.tool.run({'voltage': 12, 'resistance': '4.7k'})
        self.assertTrue(result.success)
        self.assertIn('0.00255319', result.output)  # 12/4700

    def test_single_argument_error(self):
        result = self.tool.run({'voltage': 5})
        self.assertFalse(result.success)
        self.assertIn('две', result.error)

    def test_division_by_zero(self):
        result = self.tool.run({'voltage': 5, 'current': 0})
        self.assertFalse(result.success)


class LedResistorTest(unittest.TestCase):

    def setUp(self):
        self.tool = LedResistorTool()

    def test_classic_case(self):
        result = self.tool.run({'supply_voltage': 5, 'led_voltage': 2, 'led_current': 0.02})
        self.assertTrue(result.success)
        self.assertIn('150', result.output)  # (5-2)/0.02
        self.assertIn('0.06', result.output)  # P = 3*0.02

    def test_voltage_too_low(self):
        result = self.tool.run({'supply_voltage': 2, 'led_voltage': 3.2, 'led_current': 0.02})
        self.assertFalse(result.success)
        self.assertIn('больше', result.error)

    def test_missing_required_argument(self):
        result = self.tool.run({'supply_voltage': 5, 'led_voltage': 2})
        self.assertFalse(result.success)
        self.assertIn('led_current', result.error)


class VoltageDividerTest(unittest.TestCase):

    def test_divider(self):
        result = VoltageDividerTool().run({'input_voltage': 12, 'r1': 10000, 'r2': 4700})
        self.assertTrue(result.success)
        self.assertIn('3.83', result.output)  # 12*4700/14700

    def test_non_positive_resistance(self):
        result = VoltageDividerTool().run({'input_voltage': 12, 'r1': 0, 'r2': 4700})
        self.assertFalse(result.success)


class RcFilterTest(unittest.TestCase):

    def test_cutoff_frequency(self):
        result = RcFilterTool().run({'resistance': 1000, 'capacitance': '100n'})
        self.assertTrue(result.success)
        self.assertIn('0.0001', result.output)  # tau = 1e-4 с
        self.assertIn('1591.55', result.output)  # f = 1/(2*pi*1e-4)


class ParallelResistorsTest(unittest.TestCase):

    def test_three_resistors(self):
        result = ParallelResistorsTool().run({'resistances': [1000, 2000, 3000]})
        self.assertTrue(result.success)
        self.assertIn('545.45', result.output)  # 1/(1/1000+1/2000+1/3000)

    def test_not_a_list(self):
        result = ParallelResistorsTool().run({'resistances': '1000'})
        self.assertFalse(result.success)


class McuCodegenTest(unittest.TestCase):

    def test_gpio(self):
        result = GpioCodeTool().run({'port': 'A', 'pin': 5, 'label': 'LED1'})
        self.assertTrue(result.success)
        self.assertIn('GPIOA', result.output)
        self.assertIn('GPIO_PIN_5', result.output)
        self.assertIn('GPIO_MODE_OUTPUT_PP', result.output)
        self.assertIn('LED1', result.output)

    def test_gpio_invalid_port(self):
        result = GpioCodeTool().run({'port': 'ABC', 'pin': 5})
        self.assertFalse(result.success)

    def test_gpio_invalid_pin(self):
        result = GpioCodeTool().run({'port': 'B', 'pin': 20})
        self.assertFalse(result.success)

    def test_gpio_invalid_mode_enum(self):
        result = GpioCodeTool().run({'port': 'A', 'pin': 5, 'mode': 'magic'})
        self.assertFalse(result.success)
        self.assertIn('output', result.error)

    def test_uart(self):
        result = UartCodeTool().run({'uart': 'USART1', 'baud_rate': 115200})
        self.assertTrue(result.success)
        self.assertIn('USART1', result.output)
        self.assertIn('115200', result.output)
        self.assertIn('GPIO_PIN_9', result.output)  # PA9 - TX

    def test_spi(self):
        result = SpiCodeTool().run({'spi': 'SPI1', 'baud_rate_prescaler': 32})
        self.assertTrue(result.success)
        self.assertIn('SPI1', result.output)
        self.assertIn('SPI_PHASE_1EDGE', result.output)
        self.assertIn('SPI_BAUDRATEPRESCALER_32', result.output)

    def test_spi_phase_edge(self):
        result = SpiCodeTool().run({'spi': 'SPI2', 'clock_phase': 1})
        self.assertTrue(result.success)
        self.assertIn('SPI_PHASE_2EDGE', result.output)

    def test_i2c(self):
        result = I2cCodeTool().run({'i2c': 'I2C1', 'clock_speed': 400000})
        self.assertTrue(result.success)
        self.assertIn('I2C1', result.output)
        self.assertIn('400000', result.output)
        self.assertIn('I2C_DUTYCYCLE_16_9', result.output)

    def test_i2c_invalid_speed(self):
        result = I2cCodeTool().run({'i2c': 'I2C1', 'clock_speed': 123})
        self.assertFalse(result.success)


class RegistryTest(unittest.TestCase):

    def test_register_and_get(self):
        registry = ToolRegistry()
        registry.register(OhmsLawTool())
        self.assertIsNotNone(registry.get('ohms_law'))
        self.assertIsNone(registry.get('unknown_tool'))

    def test_duplicate_registration(self):
        registry = ToolRegistry()
        registry.register(OhmsLawTool())
        with self.assertRaises(ValueError):
            registry.register(OhmsLawTool())

    def test_descriptions_for_routing(self):
        registry = ToolRegistry()
        registry.register(OhmsLawTool())
        registry.register(GpioCodeTool())
        descriptions = registry.descriptions()
        self.assertIn('ohms_law', descriptions)
        self.assertIn('generate_gpio_code', descriptions)
        self.assertIn('Параметры:', descriptions)


class ContextPassingTest(unittest.TestCase):

    def test_context_reaches_tool(self):
        from ai.agent.tool_base import ToolResult

        captured = {}

        class ContextCaptureTool(Tool):
            name = 'capture_context'
            description = 'захват контекста'
            parameters = {}

            def _execute(self, arguments, context):
                captured['user_id'] = context.user_id
                return ToolResult(success=True, output='ок')

        ContextCaptureTool().run({}, ToolContext(user_id=42))
        self.assertEqual(captured['user_id'], 42)


if __name__ == '__main__':
    unittest.main()

# rd-cad-agent

Агентная система для исследования возможностей ИИ-агентов в САПР: развитие
проекта rd-cad-bot (2025) от пассивного интеллектуального ассистента к активному
ИИ-агенту, способному автономно вызывать инструменты для точных вычислений и
генерации кода.

## 1. Архитектура агентной системы

```
                        ┌──────────────────────────────┐
                        │         Telegram Bot         │
                        │   (пользовательский ввод)    │
                        └──────────────┬───────────────┘
                                       │
                    ┌──────────────────▼───────────────────┐
                    │            Agent Loop                 │
                    │  рассуждение -> вызов инструмента ->  │
                    │  результат -> ... -> окончательный    │
                    │  ответ (ограничитель итераций)        │
                    └───────┬───────────────────┬───────────┘
                            │                   │
              ┌─────────────▼───────┐   ┌───────▼────────────────┐
              │    Tool Registry    │   │     Парсер JSON        │
              │  (узел маршрутиза-  │   │  (устойчив к ошибкам   │
              │  ции по описаниям)  │   │   генерации локальной  │
              └─────────┬───────────┘   │   моделью)             │
                        │               └────────────────────────┘
    ┌───────────┬───────┴────┬────────────┬──────────────┐
    ▼           ▼            ▼            ▼              ▼
ohms_law   led_resistor  rc_filter   generate_*_code  save_memory /
divider   parallel       (расчёты     (шаблоны кода   search_memory /
(расчёт   (расчёт        электрон-   периферии       analyze_image
цепей)    резисторов)    ных comps)  STM32 HAL)      (память и зрение)
```

Ключевые компоненты (директория `ai/agent/`):

| Модуль | Назначение |
|---|---|
| `tool_base.py` | базовый класс инструмента: схема параметров, валидация аргументов, инженерная запись величин ("4.7k", "100n") |
| `registry.py` | реестр инструментов - узел маршрутизации: модель выбирает инструмент по текстовым описаниям |
| `parsing.py` | парсер вызовов: извлекает JSON из ответа модели, исправляя типичные ошибки (блоки ```json, висячие запятые, одинарные кавычки) |
| `loop.py` | цикл агентного взаимодействия с ограничителем итераций, механизмом рефлексии при ошибках и сбором метрик |
| `prompts.py` | системный промпт агента: порядок использования инструментов, формат вызова, правила выхода из цикла |
| `tools/electronics.py` | расчёты: закон Ома, резистор светодиода (+ряд E24), делитель, RC-фильтр, параллельные резисторы |
| `tools/mcu_codegen.py` | генерация шаблонов кода GPIO/UART/SPI/I2C (STM32 HAL) |
| `tools/memory_tools.py` | долговременная память как вызываемые инструменты (save/search) |
| `tools/vision.py` | анализ изображений через Vision-Language модель как инструмент |

Механизм рефлексии: при ошибке выполнения инструмента или маршрутизации агент
получает уведомление `[ОШИБКА ...]` с описанием причины и инструкцией
скорректировать аргументы, после чего повторяет вызов.

Режимы работы (команда `/mode`): активный ИИ-агент (инструменты включены) и
пассивный ассистент (инструменты выключены) - используется для сравнительного
анализа режимов.

## 2. Installation
Install packages from *requirements.txt*
```commandline
pip install -r requirements.txt
```

Install <u>**one**</u> of these libraries versions:
### GPU version (CUDA)
*llama_cpp*:
```commandline
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir
```
*torch*:
```commandline
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

*sentence-transformers*:
```commandline
pip install sentence-transformers
```

*chromadb*:
```commandline
pip install chromadb
```

### CPU version
*llama_cpp*:
```commandline
pip install llama-cpp-python
```
*torch*:
```commandline
pip install torch torchvision torchaudio
```

*sentence-transformers*:
```commandline
pip install sentence-transformers
```

*chromadb*:
```commandline
pip install chromadb
```

Допускается повторное использование окружения проекта 2025 года (зависимости
не изменились).

## 3. Usage

```commandline
python main.py
```

Команды бота:
- `/start` - начать
- `/help` - помощь
- `/clear` - очистить контекст
- `/stats` - статистика памяти
- `/summary` - показать резюме диалога
- `/mode` - переключить режим: активный ИИ-агент / пассивный ассистент
- `/tools` - список доступных инструментов агента

Конфигурация (config.ini, секция `[Agent]`):
- `enabled` - агентный режим по умолчанию (true/false);
- `max_iterations` - ограничитель количества итераций цикла;
- `show_tool_trace` - отправка пользователю трассировки вызовов инструментов.

## 4. Testing

Юнит-тесты (без модели и внешних сервисов):
```commandline
python -m unittest discover -s tests -v
```

Сценарное тестирование на реальной модели (метрики: процент успешных
многошаговых операций, среднее число итераций, время ответа):
```commandline
python evaluation/run_scenarios.py --mode agent       # активный ИИ-агент
python evaluation/run_scenarios.py --mode assistant   # пассивный ассистент (для сравнения)
```

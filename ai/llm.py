from configparser import ConfigParser

from llama_cpp import Llama
from llama_cpp.llama_chat_format import Qwen25VLChatHandler

from services.service_locator import ServiceLocator


class Llm:
    def __init__(self, service_locator: ServiceLocator):
        self._config: ConfigParser = service_locator.get(ConfigParser.__name__)

        self._chat_handler = Qwen25VLChatHandler(clip_model_path=self._config['Llm']['clip_model_path'])

        self._llm = Llama(
            model_path=self._config['Llm']['model_path'],
            n_threads=int(self._config['Llm']['n_threads']),
            n_ctx=int(self._config['Llm']['n_ctx']),                     # Uncomment to increase the context window
            n_gpu_layers=int(self._config['Llm']['n_gpu_layers']),       # Uncomment to use GPU acceleration
            chat_handler=self._chat_handler
            #chat_format=self._config['Llm']['chat_format']
        )

    def generate(self, messages) -> str:
        response = self._llm.create_chat_completion(
            temperature=0.7,
            messages=messages
        )

        return response['choices'][0]['message']['content']

    def generate_with_image(self, text: str, image_path: str) -> str:
        """Генерация ответа с учетом изображения"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"file://{image_path}"}},
                    {"type": "text", "text": text}
                ]
            }
        ]

        response = self._llm.create_chat_completion(
            temperature=0.7,
            messages=messages
        )
        return response['choices'][0]['message']['content']

from configparser import ConfigParser

from llama_cpp import Llama

from services.service_locator import ServiceLocator


class Llm:
    def __init__(self, service_locator: ServiceLocator):
        self._config: ConfigParser = service_locator.get(ConfigParser.__name__)
        self._llm = Llama(
            model_path=self._config['Llm']['model_path'],
            n_threads=int(self._config['Llm']['n_threads']),
            n_ctx=int(self._config['Llm']['n_ctx']),                     # Uncomment to increase the context window
            n_gpu_layers=int(self._config['Llm']['n_gpu_layers']),       # Uncomment to use GPU acceleration
            chat_format=self._config['Llm']['chat_format']
        )

    def generate(self, messages) -> str:
        response = self._llm.create_chat_completion(
            temperature=0.7,
            messages=messages
        )

        return response['choices'][0]['message']['content']

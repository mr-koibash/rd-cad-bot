import os
from configparser import ConfigParser

from ai.llm import Llm
from ai.long_term_memory import LongTermMemory
from bot import TelegramBot
from db.holders import DbRepositoriesHolder
from services.service_locator import ServiceLocator


if __name__ == '__main__':
    service_locator = ServiceLocator()

    current_dir = os.path.dirname(__file__)
    config = ConfigParser()
    config.read(f'{current_dir}/config.ini')
    service_locator.add(ConfigParser.__name__, config)

    # repositories
    db_config = config['Db']
    repositories = DbRepositoriesHolder('main main main', db_config)
    service_locator.add(DbRepositoriesHolder.__name__, repositories)

    # RAG
    long_term_memory = LongTermMemory(db_path=".chroma_memory")
    service_locator.add(LongTermMemory.__name__, long_term_memory)

    # ai
    llm = Llm(service_locator)
    service_locator.add(Llm.__name__, llm)

    # bot
    bot = TelegramBot(service_locator)
    bot.run()

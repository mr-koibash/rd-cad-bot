import os
from configparser import ConfigParser

from ai.llm import Llm
from ai.long_term_memory import LongTermMemory
from ai.summarizer import DialogSummarizer
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

    # ai
    llm = Llm(service_locator)
    service_locator.add(Llm.__name__, llm)

    # RAG
    long_term_memory = LongTermMemory(db_path=config['LongTermMemory']['chroma_directory'])
    service_locator.add(LongTermMemory.__name__, long_term_memory)

    # summarizer
    summarizer = DialogSummarizer(llm, config)
    service_locator.add(DialogSummarizer.__name__, summarizer)

    # bot
    bot = TelegramBot(service_locator)
    bot.run()

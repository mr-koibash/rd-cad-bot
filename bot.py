import logging
from configparser import ConfigParser
from datetime import datetime

import telebot

from ai.llm import Llm
from ai.prompts import cad_prompt, ai_friend_prompt
from db.holders import DbRepositoriesHolder
from logger.console import ConsoleLogger
from services.service_locator import ServiceLocator


class TelegramBot:
    def __init__(self, service_locator: ServiceLocator):
        self._config: ConfigParser = service_locator.get(ConfigParser.__name__)
        self._repositories: DbRepositoriesHolder = service_locator.get(DbRepositoriesHolder.__name__)
        self._llm: Llm = service_locator.get(Llm.__name__)

        # logger
        self._logger = ConsoleLogger(TelegramBot.__name__, logging.DEBUG)

        # bot initialize
        self.bot = telebot.TeleBot(self._config['Telegram']['token'])
        self.register_handlers()

    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start(message):
            self.send_welcome(message)

        @self.bot.message_handler(commands=['help'])
        def help(message):
            self.send_help(message)

        @self.bot.message_handler(commands=['clear'])
        def clear_dialog(message):
            self.clear_dialog(message)

        @self.bot.message_handler()
        def dialog_message(message):
            self.reply(message)

    def clear_dialog(self, message):
        self._repositories.user_messages.delete_user_messages(message.from_user.id)
        self.bot.reply_to(message, 'История диалога успешно удалена. Я всё забыл...')


    def send_welcome(self, message):
        self._logger.info(f'User {message.from_user.id} joined.')
        user = message.from_user
        if self._repositories.users.get_user(user.id, user.first_name) is None:
            self._repositories.users.add_user(user.id, user.first_name)
            self.bot.reply_to(message, 'Добрый день! Я ИИ-ассистент и моя цель - '
                                       'помогать инженерам в системах автоматизированного проектирования. '
                                       'Чем я могу быть Вам полезен?')
        else:
            self.bot.reply_to(message, 'Наша работа уже начата и идёт полным ходом!')

    def send_help(self, message):
        self.bot.reply_to(message, 'Доступные команды:\n/start - Начать\n/help - Помощь\n/clear - Очистить контекст')

    def reply(self, message):
        self._logger.info(f'Input message - user id: {message.from_user.id}, message: {message.text}')
        self._repositories.user_messages.add_user_message(message.from_user.id, message.text, is_user_input=True)

        # create dialog content
        current_date_time = datetime.now().strftime('%d %B %Y, %H:%M MSK')
        messages = [{'role': 'system', 'content': cad_prompt + f'\n\nТекущее время: {current_date_time}'}]

        dialog = self._repositories.user_messages.get_user_messages(message.from_user.id)
        if dialog is None:
            dialog = []
        for dialog_message in reversed(dialog):
            role = 'user' if dialog_message.is_user_input else 'assistant'
            messages.append({'role': role, 'content': dialog_message.message})

        # llm
        response = self._llm.generate(messages)

        # save response and send to user
        self._logger.info(f'Bot\'s response: {response}')
        self._repositories.user_messages.add_user_message(message.from_user.id, response, is_user_input=False)

        self.bot.send_message(message.chat.id, response)

    def run(self):
        self._logger.info(f'AI CAD helper bot started')
        self.bot.infinity_polling()

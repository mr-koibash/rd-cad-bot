import logging
from configparser import ConfigParser
from datetime import datetime

import telebot

from ai.llm import Llm
from ai.long_term_memory import LongTermMemory
from ai.prompts import cad_prompt, ai_friend_prompt
from ai.summarizer import DialogSummarizer
from db.holders import DbRepositoriesHolder
from logger.console import ConsoleLogger
from services.service_locator import ServiceLocator


class TelegramBot:
    def __init__(self, service_locator: ServiceLocator):
        self._config: ConfigParser = service_locator.get(ConfigParser.__name__)
        self._repositories: DbRepositoriesHolder = service_locator.get(DbRepositoriesHolder.__name__)
        self._llm: Llm = service_locator.get(Llm.__name__)
        self._long_term_memory: LongTermMemory = service_locator.get(LongTermMemory.__name__)
        self._summarizer: DialogSummarizer = service_locator.get(DialogSummarizer.__name__)

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

        @self.bot.message_handler(commands=['stats'])
        def memory_stats(message):
            self.show_memory_stats(message)

        @self.bot.message_handler(commands=['summary'])
        def show_summary(message):
            self.show_summary(message)

        @self.bot.message_handler()
        def dialog_message(message):
            self.reply(message)

    def clear_dialog(self, message):
        self._repositories.user_messages.delete_user_messages(message.from_user.id)
        self._long_term_memory.clear_memory(message.from_user.id)
        self.bot.reply_to(message, 'История диалога успешно удалена. Я всё забыл...')

    def show_memory_stats(self, message):
        """Показать статистику памяти"""
        stats = self._long_term_memory.get_memory_stats(message.from_user.id)

        response = f"📊 Статистика памяти:\n"
        response += f"💬 Сохранённых взаимодействий: {stats['total_interactions']}\n"

        self.bot.reply_to(message, response)

    def show_summary(self, message):
        """Показать текущее резюме диалога"""
        summary = self._repositories.users.get_summary_by_id(message.from_user.id)
        response = f"📋 Резюме нашего диалога:\n\n{summary}"
        self.bot.reply_to(message, response)

    def send_welcome(self, message):
        self._logger.info(f'User {message.from_user.id} joined.')
        user = message.from_user
        if self._repositories.users.get_user(user.id) is None:
            self._repositories.users.add_user(user.id, user.first_name)
            self.bot.reply_to(message, 'Добрый день! Я ИИ-ассистент и моя цель - '
                                       'помогать инженерам в системах автоматизированного проектирования. '
                                       'Чем я могу быть Вам полезен?')
        else:
            self.bot.reply_to(message, 'Наша работа уже начата и идёт полным ходом!')

    def send_help(self, message):
        self.bot.reply_to(message, 'Доступные команды:\n'
                                   '/start - Начать\n'
                                   '/help - Помощь\n'
                                   '/clear - Очистить контекст\n'
                                   '/stats - Статистика памяти\n'
                                   '/summary - Показать резюме диалога')

    def reply(self, message):
        user_id = message.from_user.id

        self._logger.info(f'Input message - user id: {user_id}, message: {message.text}')
        self._repositories.user_messages.add_user_message(user_id, message.text, is_user_input=True)

        user = self._repositories.users.get_user(user_id)
        current_summary = user.summary

        # get relevant context from long-term memory
        long_term_context = self._long_term_memory.get_relevant_context(
            user_id=message.from_user.id,
            query=message.text,
            n_results=3  # top-3 relevant memories
        )

        # create dialog content with long-term memory
        current_date_time = datetime.now().strftime('%d %B %Y, %H:%M MSK')
        system_prompt = cad_prompt + f'\n\nТекущее время: {current_date_time}\n'
        # add summary
        system_prompt += f'КРАТКОЕ РЕЗЮМЕ ПРЕДЫДУЩИХ ДИАЛОГОВ: {current_summary}\n\n'
        # add RAG
        if long_term_context:
            system_prompt += 'Ниже твои воспоминания из прошлого диалога с пользователем. Учти эти сообщения, если они релевантны запросу пользователя:'
            system_prompt += f'\n\n{long_term_context}\n\n'
        messages = [{'role': 'system', 'content': system_prompt}]
        # add short-term memory (latest N messages)
        dialog = self._repositories.user_messages.get_user_messages(message.from_user.id)
        if dialog is None:
            dialog = []
        for dialog_message in reversed(dialog):
            role = 'user' if dialog_message.is_user_input else 'assistant'
            messages.append({'role': role, 'content': dialog_message.message})

        # generate response
        response = self._llm.generate(messages)
        self._logger.info(f'Bot\'s response: {response}')

        # save response to long-term (RAG) and short-term (DB) memory
        self._repositories.user_messages.add_user_message(message.from_user.id, response, is_user_input=False)
        self._long_term_memory.save_interaction(
            user_id=message.from_user.id,
            user_message=message.text,
            bot_response=response,
            metadata={
                'timestamp': current_date_time,
                'message_length': len(message.text)
            }
        )

        unsummated_messages_counter = user.unsummated_messages_counter + 1

        if self._summarizer.should_create_summary(unsummated_messages_counter):
            self._logger.info(f"⏳ Creating summary for {user_id} {user.first_name}...")
            dialog_part = self._repositories.user_messages.get_user_messages(user_id, limit=30)
            messages_to_summarize = []
            for dialog_message in reversed(dialog_part):  # latest 30
                role = 'user' if dialog_message.is_user_input else 'assistant'
                messages_to_summarize.append({
                    'role': role,
                    'content': dialog_message.message
                })

            try:
                new_summary = self._summarizer.create_summary(
                    messages=messages_to_summarize,
                    existing_summary=current_summary
                )
                self._repositories.users.update_summary_by_id(user_id, new_summary)
                unsummated_messages_counter = 0
                self._logger.info(f"✅ Summary updated for user {user_id} {user.first_name}")

            except Exception as e:
                self._logger.error(f"❌ Error in summary creating: {e}")

        self._repositories.users.update_unsummated_counter_by_id(user_id, unsummated_messages_counter)

        # send response to user
        self.bot.send_message(message.chat.id, response)

    def run(self):
        self._logger.info(f'AI CAD helper bot started')
        self.bot.infinity_polling()

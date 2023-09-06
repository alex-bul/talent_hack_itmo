from telebot import TeleBot

from telebot.types import BotCommand, Message

from ai_module.chatgpt import GPT_MODEL, ask_chat_gpt
from core.config import BOT_TOKEN
from db.methods import set_chat_mode, get_user

bot = TeleBot(token=BOT_TOKEN)

chat_gpt_context = {}

bot.set_my_commands([
    BotCommand('/wiki', 'Поиск по вики'),
    BotCommand('/chatgpt', 'Общение с ChatGPT'),
    BotCommand('/calendar', 'Взаимодействие с календарем'),
    BotCommand('/help', 'Справочная информация')
])


def handle_wiki(message: Message):
    user_telegram_id = message.from_user.id
    bot.send_message(user_telegram_id, "Не найдено!")


def handle_chatgpt(message: Message):
    user_telegram_id = message.from_user.id
    bot.send_chat_action(user_telegram_id, action='typing', timeout=100)
    bot.send_message(user_telegram_id, ask_chat_gpt(text=message.text))


def handle_calendar(message: Message):
    user_telegram_id = message.from_user.id
    bot.send_message(user_telegram_id, "Ошибка")


mods_info = {
    'wiki': ("Сформулируй свой вопрос в свободной форме, а я попробую найти ответ на него 🙃", handle_wiki),
    'chatgpt': (f"ChatGPT ({GPT_MODEL}) на связи, задавай свой вопрос 👇", handle_chatgpt),
    'calendar': ('В разработке...', handle_calendar)
}


@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    bot.send_message(message.chat.id, "Привет! Это AI-ассистент ✨\n\n"
                                      "/wiki — умный поиск по базе знаний компании\n"
                                      "/chatgpt — пообщаться с chatGPT\n"
                                      "/calendar — взаимодействие с Яндекс.Календарь\n\n"
                                      "Любую команду всегда можно вызвать из меню в нижнем левом углу")


@bot.message_handler(commands=['wiki', 'chatgpt', 'calendar'])
def handle_chat_mode_change(message: Message):
    user_telegram_id = message.from_user.id
    command = message.text.strip('/')

    for mode, (answer, handler) in mods_info.items():
        if command.startswith(mode):
            bot.send_message(user_telegram_id, answer)
            set_chat_mode(user_telegram_id, mode)
            break


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_telegram_id = message.from_user.id
    user = get_user(user_telegram_id)

    for mode, (answer, handler) in mods_info.items():
        if user.chat_mode == mode:
            handler(message)
            break



# @bot.message_handler(content_types=['voice'])
# def voice_handler(message):
#     chat_id = message.chat.id
#
#     bot.send_chat_action(chat_id, action='typing', timeout=100)
#
#     bot_message, text, error = voice_message_to_text(message)
#
#     bot.send_message(chat_id, bot_message)
#
#     if not error:
#         message_handler(message, text)


bot.polling(none_stop=True)

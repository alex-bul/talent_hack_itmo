import json
import requests

from telebot import TeleBot

from telebot.types import BotCommand, Message

from ai_module.chatgpt import GPT_MODEL, ask_chat_gpt
from core.config import BOT_TOKEN
from db.methods import set_chat_mode, get_user

bot = TeleBot(token=BOT_TOKEN)

CHATGPT_CONTEXT = {}
CONTEXT_SIZE = 1000

bot.set_my_commands([
    BotCommand('/wiki', 'Поиск по вики'),
    BotCommand('/chatgpt', 'Общение с ChatGPT'),
    BotCommand('/calendar', 'Взаимодействие с календарем'),
    BotCommand('/help', 'Справочная информация')
])


def context_size_change(user_telegram_id):
    res = []
    size = 0
    for i, mes in enumerate(CHATGPT_CONTEXT[user_telegram_id][::-1]):
        res.append(mes)
        size += len(mes)
        if size >= CONTEXT_SIZE:
            break
    CHATGPT_CONTEXT[user_telegram_id] = res[::-1].copy()
    return res[::-1]


def handle_wiki(message: Message):
    user_telegram_id = message.from_user.id
    bot.send_chat_action(user_telegram_id, action='typing', timeout=100)
    text = message.text
    if user_telegram_id not in CHATGPT_CONTEXT:
        CHATGPT_CONTEXT[user_telegram_id] = []
    CHATGPT_CONTEXT[user_telegram_id].append(text)
    try:
        url = "http://backend:8000/query"

        payload = json.dumps({
            "message": text,
            "use_gpt": True,
            "context": context_size_change(user_telegram_id),
            "clarify": True
        })
        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload).json()

        answer = response['message']
        source = response['source']
        if answer:
            bot.send_message(user_telegram_id, answer + f"\n\nИсточник: {source}")
            CHATGPT_CONTEXT[user_telegram_id].append(answer)
        else:
            raise Exception("answer == None, ошибка на стороне сервер")
    except Exception as ex:
        print(ex)
        bot.send_message(user_telegram_id, "Произошла ошибка, отправьте вопрос еще раз")


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
            if mode == 'wiki':
                CHATGPT_CONTEXT[user_telegram_id] = []
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


bot.polling(none_stop=True)

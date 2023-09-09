import json
import requests
import re

from telebot import TeleBot

from telebot.types import BotCommand, Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, \
    ReplyKeyboardMarkup, KeyboardButton

from ai_module.chatgpt import GPT_MODEL, ask_chat_gpt
from core.config import BOT_TOKEN
from db.methods import set_chat_mode, get_user

bot = TeleBot(token=BOT_TOKEN)

CHATGPT_CONTEXT = {}
CONTEXT_SIZE = 1000

SLOTS = {
    "Михаил Иванов Сергеевич": [1, 0, 0, 0, 1, 1, 0, 0, 0],
    "Сергей Иванов Сергеевич": [0, 1, 1, 0, 1, 1, 0, 0, 0],
    "Егор Иванов Сергеевич": [0, 0, 0, 0, 0, 0, 0, 0, 0],

}

calendar_keyboard = InlineKeyboardMarkup()
calendar_keyboard.add(InlineKeyboardButton("Слоты", callback_data='slots'))
calendar_keyboard.add(InlineKeyboardButton("Создать встречу", callback_data='meetings'))

slots_keyboard = InlineKeyboardMarkup()
for name in SLOTS.keys():
    slots_keyboard.add(InlineKeyboardButton(text=name, callback_data="select_slot_" + name))
slots_keyboard.add(InlineKeyboardButton("Назад", callback_data="back_calendar"))


def get_person_slot_keyboard(person):
    keyboard = InlineKeyboardMarkup()
    row = []
    for i in range(9, 18):
        if SLOTS[person][i - 9] == 0:
            row.append(InlineKeyboardButton(text=f"{i}:00-{i + 1}:00", callback_data=f'slot_{person}+{i}:{i + 1}'))
        if len(row) == 3 or (i == 17 and row):
            keyboard.add(*row)
            row.clear()
    keyboard.add(InlineKeyboardButton("Назад", callback_data=f"back_slots_{name}"))
    return keyboard


meeting_keyboard = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
meeting_keyboard.add(KeyboardButton("Отмена"))

MEETING_PIPELINE_HINTS = [
    ["Когда? Укажите дату встречи в формате ДД.ММ.ГГ ММ.ЧЧ (например, 09.09.23 11.00)", 'datetime'],
    ["Кого позовем? Напишите в столбик email-ы всех участников встречи", 'email'],
    ["Что будет? Укажите заголовок встречи", 'title'],
    ["Теперь заполним описание. Можете описать подробности насколько считаете необходимым, "
     "но обязательно укажите **ссылку, по которой участники смогут подключиться**!", 'description'],
]


def meeting_data_getter(message: Message, step_index=0, context=None):
    if context is None:
        context = {}

    if message.text == 'Отмена':
        bot.send_message(message.chat.id,
                         "Выберите интересующую функцию", reply_markup=calendar_keyboard)
        return

    if step_index > 0:
        text = message.text
        previous_key = MEETING_PIPELINE_HINTS[step_index - 1][1]
        if previous_key == 'datetime' and not bool(re.match(r"\d{2}\.\d{2}\.\d{2} \d{2}\.\d{2}", text)):
            message = bot.send_message(message.chat.id, "Неверный формат даты", parse_mode='markdown',
                                       reply_markup=meeting_keyboard)
            bot.register_next_step_handler(message, meeting_data_getter, step_index, context)
            return
        elif previous_key == 'email' and '@' not in text:
            message = bot.send_message(message.chat.id, "Вы не указали **email-ы** в сообщении", parse_mode='markdown',
                                       reply_markup=meeting_keyboard)
            bot.register_next_step_handler(message, meeting_data_getter, step_index, context)
            return
        elif previous_key == 'description' and 'http' not in text:
            message = bot.send_message(message.chat.id, "Вы не указали **ссылку** в сообщении!", parse_mode='markdown',
                                       reply_markup=meeting_keyboard)
            bot.register_next_step_handler(message, meeting_data_getter, step_index, context)
            return
        context[MEETING_PIPELINE_HINTS[step_index - 1][1]] = text

    if step_index < len(MEETING_PIPELINE_HINTS):
        message = bot.send_message(message.chat.id, MEETING_PIPELINE_HINTS[step_index][0], parse_mode='markdown',
                                   reply_markup=meeting_keyboard)
        bot.register_next_step_handler(message, meeting_data_getter, step_index + 1, context)
    else:
        bot.send_message(message.chat.id,
                         f"**Встреча успешно отправлена на согласование!**\n\n🔸" + '\n🔸'.join(context.values()),
                         parse_mode='markdown')


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
            bot.send_message(user_telegram_id,
                             "Не получилось найти ответ на вопрос. Задайте другой или попробуйте позднее."
                             "\n\nВы также можете задать вопрос одному из наших сотрудников: "
                             "@alexbul0 или @S_Statsenko")
    except Exception as ex:
        print(ex)
        bot.send_message(user_telegram_id, "Произошла ошибка, отправьте вопрос еще раз")


def handle_chatgpt(message: Message):
    user_telegram_id = message.from_user.id
    bot.send_chat_action(user_telegram_id, action='typing', timeout=100)
    bot.send_message(user_telegram_id, ask_chat_gpt(text=message.text))


def handle_calendar(message: Message):
    user_telegram_id = message.from_user.id
    bot.send_message(user_telegram_id, f"Выберите интересующую функцию", reply_markup=calendar_keyboard)


mods_info = {
    'wiki': ("Сформулируй свой вопрос в свободной форме, а я попробую найти ответ на него 🙃", handle_wiki),
    'chatgpt': (f"ChatGPT ({GPT_MODEL}) на связи, задавай свой вопрос 👇", handle_chatgpt),
    'calendar': ('Выберите интересующую функцию', handle_calendar)
}


@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    bot.send_message(message.chat.id, "Привет! Это AI-ассистент ✨\n\n"
                                      "/wiki — умный поиск по базе знаний компании\n"
                                      "/chatgpt — пообщаться с chatGPT\n"
                                      "/calendar — взаимодействие с календарем\n\n"
                                      "Любую команду всегда можно вызвать из меню в нижнем левом углу")


@bot.message_handler(commands=['wiki', 'chatgpt', 'calendar'])
def handle_chat_mode_change(message: Message):
    user_telegram_id = message.from_user.id
    command = message.text.strip('/')

    for mode, (answer, handler) in mods_info.items():
        if command.startswith(mode):
            set_chat_mode(user_telegram_id, mode)
            if mode == 'wiki':
                CHATGPT_CONTEXT[user_telegram_id] = []
            if mode == 'calendar':
                bot.send_message(user_telegram_id, answer, reply_markup=calendar_keyboard)
                break
            bot.send_message(user_telegram_id, answer)
            break


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_telegram_id = message.from_user.id
    user = get_user(user_telegram_id)

    for mode, (answer, handler) in mods_info.items():
        if user.chat_mode == mode:
            handler(message)
            break


# Обработчик callback кнопки
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call: CallbackQuery):
    if call.data == 'slots' or call.data.startswith('back_slots'):
        bot.edit_message_text(f"Выберите сотрудника, который вас интересует", call.message.chat.id,
                              call.message.message_id, reply_markup=slots_keyboard)
    elif call.data == 'meetings':
        bot.edit_message_text(f"Нажмите **Отмена**, чтобы выйти из создания встречи", call.message.chat.id,
                              call.message.message_id, parse_mode='markdown')
        meeting_data_getter(call.message)
    elif call.data.startswith("select_slot"):
        person = call.data.split('_')[2]
        bot.edit_message_text(f"Доступные слоты сотрудника {person}", call.message.chat.id, call.message.message_id,
                              reply_markup=get_person_slot_keyboard(person))
    elif call.data.startswith('back'):
        if 'calendar' in call.data:
            bot.edit_message_text(f"Выберите интересующую функцию", call.message.chat.id,
                                  call.message.message_id, reply_markup=calendar_keyboard)
    elif call.data.startswith('slot_'):
        info = call.data.split('_')[1]
        person, time = info.split('+')
        start, end = time.split(':')
        bot.send_message(call.message.chat.id,
                         f"🚀 Запрос на бронирование слота ({person}, {start}-{end}) успешно отправлен!")
        SLOTS[person][int(start) - 9] = 1
        bot.edit_message_text(f"Доступные слоты сотрудника {person}", call.message.chat.id, call.message.message_id,
                              reply_markup=get_person_slot_keyboard(person))


bot.polling(none_stop=True)

from db.database import *


def get_user(user_telegram_id) -> User:
    return User.get_or_create(telegram_id=user_telegram_id)[0]


def set_chat_mode(user_telegram_id: int, chat_mode: str):
    """

    :param user_telegram_id:
    :param chat_mode: [chatgpt, wiki, calendar]
    :return:
    """
    user = get_user(user_telegram_id)
    user.chat_mode = chat_mode
    user.save()

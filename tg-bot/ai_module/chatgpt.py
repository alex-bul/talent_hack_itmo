import json
import logging
import time
import random
import requests

from core.tools import hand_error
from ai_module.tools import is_contain_bad_words
from ai_module.token_manager import api_keys, delete_key, rate_limit_api_key, get_token

from ai_module.tools import get_content

URL_BASE = 'https://api.openai.com'
GPT_MODEL = "gpt-3.5-turbo-16k"

# Сообщение в случае ошибки сервера
ERROR_MESSAGE = "Произошла ошибка, попробуйте снова"

# Базовый промпт, задающий поведение модели
system_message = "You are helpful assistant for work tasks in «Napoleon IT» (name of company)"

base_context = [
    {'role': 'system',
     'content': system_message},
]

functions = [
    {
        "name": "open_url",
        "description": "Get content from website url and give feedback on it",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Link to website page, e.g. https://google.com",
                },
                "task": {
                    "type": "string",
                    "enum": ["summarize", "analyze"],
                    "description": "What need to do with url: summarize text or analyze it",
                },
            },
            "required": ["url", "task"],
        },
    }
]


def open_url(url: str, task: str):
    """Получает текстовое содержимое сайта и присылает краткое содержание или своё мнение касательно данной информации.
     Исполняемое действие зависит от просьбы пользователя"""
    try:
        content = get_content(url)

        if task == 'summarize':
            prompt = f'Вот содержание веб страницы ({url}), напиши её краткое содержание:\n\n' + content
        elif task == 'comment':
            prompt = f'Вот содержание веб страницы ({url}), прокоментируй, вырази своё мнение:\n\n' + content
        else:
            raise ValueError('task only summarize or comment')

        messages = base_context + [
            {'role': 'user',
             'content': prompt}
        ]
        res = ask_chat_gpt(messages=messages, functions_gpt=False)
        return res
    except RuntimeError as ex:
        hand_error(ex)
        return ERROR_MESSAGE


working_functions = {
    'open_url': open_url,
}


def change_system_message(new_text):
    global system_message, base_context

    system_message = new_text
    base_context = [
        {'role': 'system',
         'content': system_message}
    ]


def get_system_message():
    return system_message


def ask_chat_gpt(text=None, messages=None, user_info=None, apply_system_context=True, functions_gpt=None):
    if messages is None:
        messages = []

    if functions_gpt is None:
        functions_gpt = functions
    else:
        functions_gpt = None

    if text:
        messages.append({
            'role': 'user',
            'content': text
        })

    if apply_system_context:
        messages = base_context + messages

    if user_info:
        messages[-1]['content'] = f"{user_info} writes to you: " + messages[-1]['content']

    dta = chat_completion_request(messages, functions=functions_gpt)

    if dta['content'] is None and dta['function_call']:
        worker = working_functions[dta['function_call']['name']]
        return worker(**json.loads(dta['function_call']['arguments']))
    elif dta.get('content', None) is not None:
        return dta['content']
    else:
        return ERROR_MESSAGE


def chat_completion_request(messages, functions=None, function_call=None, model=GPT_MODEL,
                            generate_exceptions=True, max_tokens=4096, return_raw=False, n_message=1) -> dict:
    json_data = {"model": model, "messages": messages, "max_tokens": max_tokens, 'n': n_message}
    if functions is not None:
        json_data.update({"functions": functions})
    if function_call is not None:
        json_data.update({"function_call": function_call})
    try:
        if len(api_keys) == 0:
            return {'content': ERROR_MESSAGE}
        api_key = get_token()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        url = URL_BASE + '/v1/chat/completions'

        data = requests.post(url, json=json_data, headers=headers, timeout=30).json()

        if 'error' in data:
            if 'insufficient_quota' == data['error']['type'] or data['error']['code'] == 'account_deactivated':
                delete_key(api_key)
                logging.info(f"Токен истек {api_key}")
                return chat_completion_request(messages, functions, function_call, model, generate_exceptions)
            elif data['error']['code'] == 'rate_limit_exceeded':
                rate_limit_api_key(api_key)
                logging.info(f"Токен лимит {api_key}")
                return chat_completion_request(messages, functions, function_call, model, generate_exceptions)
            elif 'server_error' == data['error']['type']:
                raise RuntimeError("server error")
            else:
                logging.error(f"ОШИБКА CHOICES {str(data)}")
                raise RuntimeError("ОШИБКА CHOICES")

        if return_raw:
            return data['choices']

        message_object = data["choices"][0]['message']
        if message_object['content'] and is_contain_bad_words(message_object['content']):
            return {'content': 'Мне кажется, что стоит сменить тему разговора'}
        return message_object
    except Exception as ex:
        hand_error(ex)
        return {}


def get_answer_variants(messages, n_message=3):
    choices = chat_completion_request(messages=messages,
                                      return_raw=True, n_message=n_message)
    answer_variants = []
    for mes in choices:
        answer_variants.append(mes['message']['content'])
    return answer_variants


def describe_conversation(context: list, max_tokens, prompt):
    context.append(
        {
            'role': 'system',
            'content': prompt
        }
    )
    for i in range(3):
        try:
            res = chat_completion_request(messages=context, max_tokens=max_tokens)
            return res['content']
        except:
            pass
        time.sleep(1)
    raise RuntimeError('chatgpt api error')

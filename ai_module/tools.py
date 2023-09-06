import os

import requests
from bs4 import BeautifulSoup

from pymorphy2 import MorphAnalyzer

current_path = os.path.dirname(__file__)
bad_words_file = os.path.join(current_path, 'bad_words.txt')

with open(bad_words_file, 'r', encoding='utf-8') as f:
    bad_words = set([i.strip() for i in f.readlines()])


def is_contain_bad_words(text):
    if text is None:
        return False

    morph = MorphAnalyzer()
    words = text.lower().split()

    for w in words:
        normal_form = morph.parse(w)[0].normal_form
        if normal_form in bad_words:
            return True

    return False


def get_content(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError('ошибка запроса')

    # парсим HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    try:
        # берём заголовок страницы
        title = soup.title.string.strip()
    except AttributeError:
        title = ''

    # берём текст из h1, h2, h3, p, b
    valid_tags = ['h1', 'h2', 'h3', 'p', 'b', 'span']
    texts = [tag.get_text() for tag in soup.find_all(valid_tags)]

    # объединяем текст в строку
    page_text = ' '.join(texts)[:3000]

    return f"{url}\n{title}\n{page_text}"

import os
import time
import threading

from core.log import logger

current_path = os.path.dirname(__file__)

API_KEYS_FILE = os.path.join(current_path, 'api_keys.txt')
EXCEEDED_KEYS_FILE = os.path.join(current_path, 'exceeded_keys_file.txt')
API_KEY_CURRENT_INDEX = 0

api_keys = []
# [(time, key), (time,key)]
rate_limit_api_keys = []


def get_token():
    global API_KEY_CURRENT_INDEX

    API_KEY_CURRENT_INDEX += 1
    return api_keys[API_KEY_CURRENT_INDEX % len(api_keys)]


def update_api_keys():
    with open(API_KEYS_FILE, 'r', encoding='utf-8') as f:
        current_list = [key.strip() for key in f.readlines() if key.strip()]
    current_list = set(current_list)
    current_list -= set(api_keys)

    good_keys = map(lambda x: x[1], filter(lambda x: time.time() - x[0] >= 20, rate_limit_api_keys))
    bad_keys = set(rate_limit_api_keys) - set(good_keys)
    current_list -= bad_keys

    api_keys.extend(list(good_keys))
    api_keys.extend(list(current_list))


def delete_key(key):
    if key not in api_keys:
        return

    logger.info("Токен потратил свой лимит")
    api_keys.remove(key)
    with open(API_KEYS_FILE, 'w', encoding="utf-8") as f:
        f.write('\n'.join(api_keys))

    if EXCEEDED_KEYS_FILE not in os.listdir():
        with open(EXCEEDED_KEYS_FILE, 'w', encoding='utf-8') as f:
            f.write(key)
    else:
        with open(EXCEEDED_KEYS_FILE, 'r', encoding='utf-8') as f:
            exceeded_keys = [i.strip() for i in f.readlines()]
        exceeded_keys.append(key)
        exceeded_keys = set(exceeded_keys)
        with open(EXCEEDED_KEYS_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(exceeded_keys))


def rate_limit_api_key(key):
    if key in api_keys:
        api_keys.remove(key)

    if key not in rate_limit_api_keys:
        rate_limit_api_keys.append((time.time(), key))


def api_key_updater():
    while True:
        update_api_keys()
        time.sleep(5)


t = threading.Thread(target=api_key_updater)
t.name = 'api_key_updater'
t.start()

import os
import requests

from uuid import uuid4

from ai_module.token_manager import get_token

AUDIO_DIRECTORY = 'audio_files'

if AUDIO_DIRECTORY not in os.listdir():
    os.mkdir(AUDIO_DIRECTORY)


def transcribe_audio(audio_filepath):
    url = 'https://api.openai.com/v1/audio/transcriptions'
    headers = {
        'Authorization': f'Bearer {get_token()}',
    }

    # Отправляем POST запрос
    with open(audio_filepath, 'rb') as audio_file:
        res = requests.post(url, headers=headers, data={'model': 'whisper-1'}, files={'file': audio_file})
        transcription = res.json()

        return transcription['text']


def generate_file_path():
    return os.path.join(AUDIO_DIRECTORY, f'{uuid4()}.ogg')

AI Ассистент для корпоративной деятельности на основе ChatGPT. Умеет искать по встроенной базе знаний, взаимодействует с календарем и предоставляет доступ к ChatGPT для решения рабочих задач :)

# Запуск

`git clone --recurse-submodules https://github.com/alex-bul/talent_hack_itmo`

1. Создать два .env файла по образу example в папке /llm-retriever
2. Создать папку /llm-retriever/documents и заполнить её документами в формате txt, они составляют базу знаний компании
3. В файл /tg-bot/api_keys.txt вставить в столбик токены от OpenAI API

`docker compose up --build`
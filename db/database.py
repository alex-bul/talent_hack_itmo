import os

from peewee import *

current_path = os.path.dirname(__file__)
db_file = os.path.join(current_path, 'assistant.db')
db = SqliteDatabase(db_file)


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    id = AutoField(primary_key=True)
    telegram_id = IntegerField(unique=True)
    chat_mode = CharField(null=False, default='chatgpt')


db.connect()
db.create_tables([User])

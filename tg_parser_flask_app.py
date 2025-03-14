from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
from g4f.client import Client
import os
from dotenv import load_dotenv

load_dotenv()  # Загружает переменные из .env

app = Flask(__name__)
app.config['API_ID'] = os.environ.get('API_ID', '123456')
app.config['API_HASH'] = os.environ.get('API_HASH', 'HASH123456')
app.config['SESSION_STR'] = os.environ.get('SESSION_STR', 'SESSION_STR123456')

print(f"API_ID: {app.config['API_ID']}")
print(f"API_HASH: {app.config['API_HASH']}")

client = TelegramClient(StringSession(app.config['SESSION_STR']), app.config['API_ID'], app.config['API_HASH'])

# Функция получения постов из Телеграма
async def get_tg_posts(channel_username, posts_count):
    async with client:    
        posts = []
        async for message in client.iter_messages(channel_username, limit=posts_count):  # Читаем posts_count последних сообщений
            post = f"""Данные за: {message.date.strftime("%Y-%m-%d")}
                sender_id: {message.sender_id}
                текст сообщения: {message.text}
            """  
            posts.append(post)
            # print(f"[{message.date}] {message.sender_id}: {message.text}")
    return posts


# Генерация текста согласно промпту
def process_prompt(prompt):
    client1 = Client()
    response = client1.chat.completions.create(
        # model="gpt-4o-mini", 
        model="gpt-4",
        messages=[
            {
                "role": "user", 
                "content": prompt
                }
            ],
    # Add any other necessary parameters
    )
    return response.choices[0].message.content


# Функция преобразования текстовых данных в список словарей
def get_structured_data(raw_data):
    # Разбиваем на строки и парсим в список словарей
    result = []
    for line in raw_data.split("\n"):
        parts = line.split("===")
        if len(parts) == 5:
            result.append({
                "name": parts[0].strip(),
                "price": parts[1].strip(),
                "date": parts[2].strip(),
                "stock": parts[3].strip(),
                "currency": parts[4].strip()
            })
    return result


def parse_tg_channel(channel_username, posts_count, base_prompt):
    # posts = asyncio.run(get_tg_posts(channel_username, posts_count))
    # posts = client.loop.run_until_complete(get_tg_posts(channel_username, posts_count))  # Используем event loop TelegramClient
    # loop = asyncio.new_event_loop()  # Создаём новый event loop
    # asyncio.set_event_loop(loop)     # Устанавливаем его как текущий
    # posts = loop.run_until_complete(get_tg_posts(channel_username, posts_count))  # Выполняем асинхронную функцию
    # loop = asyncio.get_event_loop()  # Получаем текущий event loop
    # task = asyncio.ensure_future(get_tg_posts(channel_username, posts_count))  # Создаём задачу
    # posts = loop.run_until_complete(task)  # Ждём выполнения
    try:
        loop = asyncio.get_running_loop()  # Получаем текущий event loop
    except RuntimeError:  # Если его нет, создаём новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    task = asyncio.ensure_future(get_tg_posts(channel_username, posts_count))
    posts = loop.run_until_complete(task)

    posts_str = "<Start_of_message>. ".join(posts)
    prompt = base_prompt + " " + posts_str
    ai_response = process_prompt(prompt)
    parsed_data = get_structured_data(ai_response)
    result = {
        'posts': posts_str,
        'ai_response': ai_response,
        'parsed_data': parsed_data
    }
    return result


@app.route('/parse-tg-channel', methods=['POST'])
def process_parsing():
    try:
        # Получение данных из запроса
        channel_username = request.json.get('channel_username', [])
        posts_count = request.json.get('posts_count', 3)
        base_prompt = request.json.get('base_prompt', '')

        result = parse_tg_channel(channel_username, posts_count, base_prompt)

        return jsonify(result)  # Преобразуем в JSON и возвращаем

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/')
def hello_world():
    return 'Hello from TG Parser!'


if __name__ == '__main__':
    app.run(debug=True)
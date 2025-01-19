import os, requests, time, datetime, json, telebot

def load_config(filename):
    with open(filename, "r", encoding='utf-8') as file:
        return json.load(file)

def save_config(filename, config):
    with open(filename, "w",encoding='utf-8') as file:
        json.dump(config, file, indent=4)

def get_max_photo_url(photo_sizes):
    max_size = 0
    max_size_url = ''
    for size in photo_sizes:
        if size['height'] * size['width'] > max_size:
            max_size = size['height'] * size['width']
            max_size_url = size['url']
    return max_size_url

def clear_folder(folder_path):
    if os.path.exists(folder_path):                         # Проверяем, существует ли путь к папке
        for root, dirs, files in os.walk(folder_path):      # Получаем список всех файлов и подпапок в папке
            for file in files:                              # Удаляем все файлы в текущей папке
                file_path = os.path.join(root, file)
                os.remove(file_path)
            for dir in dirs:                                # Удаляем все подпапки в текущей папке
                dir_path = os.path.join(root, dir)
                os.rmdir(dir_path)
    else:
        pass

def repost_to_tg(post, text_for_replace, bot, tg_chat_id):
    print('repost_to_tg begin')
    text = post['text']
    text = text.replace(text_for_replace, "")

    # Проверяем наличие репоста
    if 'copy_history' in post and len(post['copy_history']) > 0:
        copy_post = post['copy']['copy_history'][0]
        from_id = copy_post.get('from_id')
        post_id = copy_post.get('id')
        if from_id and post_id:
            text += f"\nhttps://vk.com/wall{from_id}_{post_id}"

    media = []
    audio = []
    doc = []

    for attachment in post.get('attachments', []):
        if attachment['type'] == 'photo':
            attachment_url = get_max_photo_url(attachment['photo']['sizes'])
            media.append(telebot.types.InputMediaPhoto(attachment_url))

        if attachment['type'] == 'video':
            attachment_url = f'https://vk.com/video{attachment["video"]["owner_id"]}_{attachment["video"]["id"]}'
            text += attachment_url

        if attachment['type'] == 'audio':
            audio_url = attachment['audio']['url']
            response = requests.get(audio_url, stream=True)
            track_title = f"{attachment['audio']['artist']} - {attachment['audio']['title']}"
            audio.append(telebot.types.InputMediaAudio(response.content, title=track_title))

        if attachment['type'] == 'doc':
            doc.append(telebot.types.InputMediaDocument(attachment['doc']['url']))

    # Проверяем длину текста и отправляем его отдельно
    if len(text) > 1024:
        text = text[:4096]
        media_part = [media[0]] if media else []
        if media:
            try:
                bot.send_media_group(tg_chat_id, media)
            except Exception as e:
                bot.send_message(tg_chat_id, "Ошибка при отправке медиа")
        
        try:
            bot.send_message(tg_chat_id, text)
        except Exception as e:
            bot.send_message(tg_chat_id, "Ошибка при отправке части текста")

    else:
        # Если длина текста не превышает 1024 символов
        if media:
            try:
                media[0].caption = text
                bot.send_media_group(tg_chat_id, media)
            except Exception as e:
                bot.send_message(tg_chat_id, "Ошибка при отправке поста с медиа")
        else:
            try:
                bot.send_message(tg_chat_id, text)
            except Exception as e:
                bot.send_message(tg_chat_id, "Ошибка при отправке текста")

    # Отправка аудио отдельно
    if audio:
        try:
            audio[0].caption = text
            bot.send_media_group(tg_chat_id, audio)
        except Exception as e:
            bot.send_message(tg_chat_id, "Ошибка при отправке аудио")

    # Отправка документов отдельно
    if doc:
        try:
            doc[0].caption = text
            bot.send_media_group(tg_chat_id, doc)
        except Exception as e:
            bot.send_message(tg_chat_id, "Ошибка при отправке документов")

def find_missing_post(dates, previous_post_date):
    new_main_date_index = None
    previous_date_index = None

    for index, date in enumerate(dates):
        if date <= previous_post_date:
            new_main_date_index = previous_date_index
            break
        previous_date_index = index

    # Если ни одна дата не подошла по условию
    if new_main_date_index is None:
        new_main_date_index = len(dates) - 1

    return new_main_date_index

def process_group_config(config_path):
    config = load_config(config_path)

    vk_token = config["vk_token"]
    vk_group_id = config["vk_group_id"]
    bot = telebot.TeleBot(config["tg_token"])
    tg_chat_id = config["tg_chat_id"]
    text_for_replace = config["text_for_replace"]
    previous_post_date = int(config["previous_post_date"])  # Преобразуем в int
    offset = int(config["offset"])
    count = 50
    
    vk_api_url = f'https://api.vk.com/method/wall.get?access_token={vk_token}&v=5.199&domain={vk_group_id}&count={count}&offset={offset}'
    response = requests.get(vk_api_url)
    data = response.json()['response']['items']
    dates = [item['date'] for item in data]
    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    new_main_date_index = find_missing_post(dates, previous_post_date)
    last_post_date = data[new_main_date_index]['date']
    post_data = data[new_main_date_index]
    
    if last_post_date > previous_post_date:
        repost_to_tg (post_data, text_for_replace, bot, tg_chat_id)
        config["previous_post_date"] = int(last_post_date)  # Обновляем значение в config
        save_config(config_path, config)  # Сохраняем обновленный config в файл
        print(f'{vk_group_id}: Прошлый - {previous_post_date}. Нынешний - {last_post_date}. Пост отправлен. {current_time}. Код: {response}.')
    else:
        print(f'{vk_group_id}: Прошлый - {previous_post_date}. Нынешний - {last_post_date}. Поста нет. {current_time}')

# Путь к папке с конфиг
script_dir = os.path.dirname(os.path.abspath(__file__))
config_folder = os.path.join(script_dir, 'groups')
n = 30 # Таймаут между циклами в секундах

while True:
    try:
        # Получаем список файлов в указанной папке
        config_files = os.listdir(config_folder)
        for config_file in config_files:
            if not config_file == 'config_example.json':
                # Полный путь к файлу
                config_path = os.path.join(config_folder, config_file)
                # Проверяем, является ли файл JSON
                if config_file.endswith(".json") and os.path.isfile(config_path):
                    process_group_config(config_path)
            else: pass 
    except Exception as e:
        pass
   
    time.sleep(n)

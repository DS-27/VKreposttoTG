import os, requests, time, datetime, json, telebot, yt_dlp, subprocess


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

# def video_downloader (attachment, video_url, output_path, media, text):
#     formats_output = subprocess.run(['yt-dlp', '-F', video_url], capture_output=True, text=True)
#     formats = formats_output.stdout
    
#     # Печатаем список форматов для отладки
#     print("Доступные форматы для видео:")
#     print(formats)
#     # Разбиваем вывод на строки
#     lines = formats.split('\n')
#     suitable_formats = []
#     # Ищем форматы с размером файла менее 20 МБ и выбираем первый подходящий
#     max_filesize = 0
#     format_id = None
#     for line in lines:
#         if 'MiB' in line:
#             filesize = float(line.split('MiB')[0].split('~')[-1].strip())
#             if filesize < 50 and filesize > max_filesize:  # Учитываем только подходящие форматы с максимальным размером
#                 format_id = line.split()[0]
#                 max_filesize = filesize
#     # Если формат был найден, загружаем видео с использованием этого формата
#     if format_id:
#         # Если формат был найден, загружаем видео с использованием этого формата
#         output_filename = f"{output_path}/{attachment['video']['title']}.mp4"  # Имя файла для сохранения
#         try:
#             subprocess.run(['yt-dlp', '-f', format_id, '-o', output_filename, video_url], check=True)
#             if not media:
#                 media.append(telebot.types.InputMediaVideo(open(output_filename, 'rb'), caption=text))
#             else:
#                 media.append(telebot.types.InputMediaVideo(open(output_filename, 'rb')))
#         except subprocess.CalledProcessError as e:
#             text += f"\n{video_url}"
#     return media, text

def video_downloader(attachment, video_url, output_path, media, text):
    formats_output = subprocess.run(['yt-dlp', '--list-formats', video_url], capture_output=True, text=True)
    formats = formats_output.stdout
    # Разбиваем вывод на строки
    lines = formats.split('\n')
    suitable_formats = []
    # Ищем форматы с размером файла менее 50 МБ и выбираем первый подходящий
    format_id = None  # Инициализируем переменную format_id здесь
    for line in lines:
        if 'MiB' in line:
            filesize = float(line.split('MiB')[0].split('~')[-1].strip())
            if filesize < 50:
                format_id = line.split()[0]
                suitable_formats.append((format_id, filesize))
                break  # Прерываем цикл после нахождения первого подходящего формата
    # Если формат был найден, загружаем видео с использованием этого формата
    if format_id:
        # Если формат был найден, загружаем видео с использованием этого формата
        output_filename = f"{output_path}/{attachment['video']['title']}.mp4"  # Имя файла для сохранения
        try:
            subprocess.run(['yt-dlp', '-f', format_id, '-o', output_filename, video_url], check=True)
            if not media:
                media.append(telebot.types.InputMediaVideo(open(output_filename, 'rb'), caption=text))
            else:
                media.append(telebot.types.InputMediaVideo(open(output_filename, 'rb')))
        except subprocess.CalledProcessError as e:
            text += f"\n{video_url}"
    else:
        text += f"\n{video_url}"
    return media, text

def repost_to_tg (data, text_for_replace, bot, tg_chat_id):
        post = data[0]
        text = post['text']
        text = text.replace(text_for_replace, "")
        text = text[:1024]
        media = []
        audio = []
        doc = []

        for attachment in post.get('attachments', []):
            if attachment['type'] == 'photo':
                attachment_url = get_max_photo_url(attachment['photo']['sizes'])
                if not media:
                    media.append(telebot.types.InputMediaPhoto(attachment_url, caption=text))
                else:
                    media.append(telebot.types.InputMediaPhoto(attachment_url))

            if attachment['type'] == 'video':
                attachment_url = f'https://vk.com/video{attachment["video"]["owner_id"]}_{attachment["video"]["id"]}'
                # media, text = video_downloader (attachment, attachment_url, "AutoRepostBot/tmp", media, text)
                text += attachment_url

            if attachment['type'] == 'audio':
                audio_url = attachment['audio']['url']
                response = requests.get(audio_url, stream=True)
                track_title = f"{attachment['audio']['artist']} - {attachment['audio']['title']}"
                if not media and not audio:
                    audio.append(telebot.types.InputMediaAudio(response.content, caption=text, title=track_title))
                else:
                    audio.append(telebot.types.InputMediaAudio(response.content, title=track_title))

            if attachment['type'] == 'doc':
                if not media and not audio and not doc:
                    doc.append(telebot.types.InputMediaDocument(attachment['doc']['url'], caption=text))
                else:
                    doc.append(telebot.types.InputMediaDocument(attachment['doc']['url']))
        
        if media:
            try:
                print ('Media send begin')
                bot.send_media_group(tg_chat_id, media)
                print ('Media send')
            except Exception as e:
                bot.send_message(tg_chat_id, "Ошибка при отправке поста с картинкой и/или видео")

        if audio:
            try:
                print ('Audio send begin')
                bot.send_media_group(tg_chat_id, audio)
                print ('Audio send')
            except Exception as e:
                bot.send_message(tg_chat_id, "Ошибка при отправке поста с аудио")
                
        if doc:
            try:
                print ('Documents send begin')
                bot.send_media_group(tg_chat_id, doc)
                print ('Documents send')
            except Exception as e:
                bot.send_message(tg_chat_id, "Ошибка при отправке поста с документом")

        if not media and not audio and not doc:
            try:
                bot.send_message(tg_chat_id, text)
            except Exception as e:
                bot.send_message(tg_chat_id, "Ошибка при отправке поста с текстом")
            
        # if response.status_code != 200:
        #     url = "https://api.telegram.org/bot"
        #     url += tg_token
        #     method = url + "/sendMessage"
        #     error_text = f'Ошибка отправления. Код ошибки: {response.status_code}, Текст ошибки: {response.text}'
        #     error_post = requests.post(method, data={
        #         "chat_id": tg_chat_id,
        #         "text": error_text
        #     })

        # Закрываем все файлы после отправки поста
        for file in media:
            if isinstance(file, telebot.types.InputMediaVideo):
                file.media.close()

        clear_folder("AutoRepostBot/tmp")

def process_group_config(config_path):
    config = load_config(config_path)

    vk_token = config["vk_token"]
    vk_group_id = config["vk_group_id"]
    bot = telebot.TeleBot(config["tg_token"])
    tg_chat_id = config["tg_chat_id"]
    text_for_replace = config["text_for_replace"]
    previous_post_date = int(config["previous_post_date"])  # Преобразуем в int
    offset = 0
    count = 1
    
    vk_api_url = f'https://api.vk.com/method/wall.get?access_token={vk_token}&v=5.199&domain={vk_group_id}&count={count}&offset={offset}'
    response = requests.get(vk_api_url)
    data = response.json()['response']['items']
    last_post_date = response.json()['response']['items'][0]['date']
    current_time = datetime.datetime.now().strftime('%H:%M:%S')

    if last_post_date > previous_post_date:
        repost_to_tg (data, text_for_replace, bot, tg_chat_id)
        config["previous_post_date"] = int(last_post_date)  # Обновляем значение в config
        save_config(config_path, config)  # Сохраняем обновленный config в файл
        print(f'{vk_group_id}: Прошлый - {previous_post_date}. Нынешний - {last_post_date}. Пост отправлен. {current_time}. Код: {response}.')
    else:
        print(f'{vk_group_id}: Прошлый - {previous_post_date}. Нынешний - {last_post_date}. Поста нет. {current_time}')

# Путь к папке с конфиг
config_folder = "groups"
n = 30 # Таймаут между циклами в секундах

while True:
    try:
        # Получаем список файлов в указанной папке
        config_files = os.listdir(config_folder)
        for config_file in config_files:
            if not config_file == 'config_example':
                # Полный путь к файлу
                config_path = os.path.join(config_folder, config_file)
                # Проверяем, является ли файл JSON
                if config_file.endswith(".json") and os.path.isfile(config_path):
                    process_group_config(config_path)
            else: pass 
    except Exception as e:
        pass
   
    time.sleep(n)
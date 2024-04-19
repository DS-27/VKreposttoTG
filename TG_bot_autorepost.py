import os, requests, time, datetime, json

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

def process_group_config(config_path):
    config = load_config(config_path)
    
    vk_token = config["vk_token"]
    vk_group_id = config["vk_group_id"]
    tg_token = config["tg_token"]
    tg_chat_id = config["tg_chat_id"]
    text_for_replace = config["text_for_replace"]
    previous_post_date = int(config["previous_post_date"])  # Преобразуем в int

    vk_api_url = f'https://api.vk.com/method/wall.get?access_token={vk_token}&v=5.199&domain={vk_group_id}&count=1&offset=1'
    response = requests.get(vk_api_url)
    data = response.json()['response']['items']
    last_post_date = response.json()['response']['items'][0]['date']
    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    i = 0

    if last_post_date > previous_post_date:
        post = data[0]
        text = post['text']
        text = text.replace(text_for_replace, "")
        text = text[:1024]
        photos = []
        for attachment in post.get('attachments', []):
            if attachment['type'] == 'photo':
                max_size_url = get_max_photo_url(attachment['photo']['sizes'])
                if i == 0:
                    photos.append({'type': 'photo', 'media': max_size_url, 'caption': text})
                else:
                    photos.append({'type': 'photo', 'media': max_size_url})
                i += 1

        tg_api_url = f'https://api.telegram.org/bot{tg_token}/sendMediaGroup'
        payload = {
            'chat_id': tg_chat_id,
            'media': photos,
            'caption': text
        }
        response = requests.post(tg_api_url, json=payload)

        config["previous_post_date"] = int(last_post_date)  # Обновляем значение в config
        save_config(config_path, config)  # Сохраняем обновленный config в файл

        if response.status_code != 200:
            url = "https://api.telegram.org/bot"
            url += tg_token
            method = url + "/sendMessage"
            error_text = f'Ошибка отправления. Код ошибки: {response.status_code}, Текст ошибки: {response.text}'
            error_post = requests.post(method, data={
                "chat_id": tg_chat_id,
                "text": error_text
            })

        print(f'{vk_group_id}: Прошлый - {previous_post_date}. Нынешний - {last_post_date}. Пост отправлен. {current_time}. Код: {response}.')
    else:
        print(f'{vk_group_id}: Прошлый - {previous_post_date}. Нынешний - {last_post_date}. Поста нет. {current_time}')

# Указываете папку с конфигами
config_folder = "groups"

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
   
    time.sleep(50)
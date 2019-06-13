# -*- coding: utf-8 -*-

import config
import telebot
import os
import mysql.connector as mc
import random
import shelve


def generate_keyboard(right_answer, wrong_answers):
    '''
    :param right_answer: Правильный ответ
    :param wrong_answers: Неправильные ответы
    :return: Объект кастомной клавиатуры
    '''
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    # Конактенируем правильный ответ с неправильными
    all_answers = '{};{}'.format(right_answer, wrong_answers)
    # Создаем список и записываем в него элементы
    list_items = []
    for item in all_answers.split(';'):
        list_items.append(item)
    # Перемешиваем элементы
    random.shuffle(list_items)
    # Заполняем разметку клавиатуры
    for item in list_items:
        markup.add(item)

    return markup


def set_user_game(chat_id, estimated_answer):
    '''
    Записываем пользователя в игроки и запоминаем, что он должен ответить
    :param chat_id: id пользователя
    :param estimated_answer: правильный ответ из БД
    '''
    with shelve.open(config.SHELVE_NAME) as storage:
        storage[str(chat_id)] = estimated_answer

def finish_user_game(chat_id):
    '''
    Заканичваем игру текущего пользователя и удаляем правильный ответ из хранилища
    :param chat_id: id пользователя
    '''
    with shelve.open(config.SHELVE_NAME) as storage:
        del storage[str(chat_id)]

def get_answer_for_user(chat_id):
    '''
    Получаем правильный ответ для текущего пользователя.
    :param chat_id: id пользователя
    :return: (str) правильный ответ / None
    '''
    with shelve.open(config.SHELVE_NAME) as storage:
        try:
            answer = storage[str(chat_id)]
            return answer
        # Если человек не играет, ничего не возвращаем
        except(KeyError):
            return None


bot = telebot.TeleBot(config.TOKEN)
query = ("SELECT * FROM music")


@bot.message_handler(commands=['lt'])
def find_file_ids(message):
    print(message.text)
    '''# Подготовка к кодированию
    files = []
    for file in os.listdir('res/'):
        print(file)
        files.append(file)

    # Находим уже перекодированные файлы
    coded_tracks = []
    for i in range(0, len(files)):
        if files[i].split('.')[-1] != '.ogg' or files[i].split('.')[-1] != '.mp3':
            continue

        file_name = files[i].split('.')[0]
        file_name_mp3 = '{}.mp3'.format(file_name)
        file_name_ogg = '{}.ogg'.format(file_name)

        if file_name_mp3 in files and file_name_ogg in files:
            files.remove(file_name_mp3)
            files.remove(file_name_ogg)
            if file_name not in coded_tracks:
                coded_tracks.append(file_name)

    # Убираем их из очереди
    for file_name in coded_tracks:
        file_name_mp3 = '{}.mp3'.format(file_name)
        file_name_ogg = '{}.ogg'.format(file_name)

        files.remove(file_name_mp3)
        files.remove(file_name_ogg)

    for file in files:
        file_name = file.split('.')[0]
        convert = './ffmpeg -i {}.mp3 -ac 1 -map 0:a -codec:a libopus -b:a 128k -ar 24000 {}.ogg'.format(file_name)
        print(os.system(convert))'''

    for file in os.listdir('res/'):
        if file.split('.')[-1] == 'ogg':
            buffer = open('res/'+file, 'rb')
            my_message = bot.send_voice(message.chat.id, buffer, None, timeout=30)
            bot.send_message(message.chat.id, my_message.voice.file_id, reply_to_message_id=my_message.message_id)


@bot.message_handler(commands=['gm'])
def gm(message):
    print(message.text)
    # Подключаемся к БД и достаем случайный трек
    mysql_connect = mc.connect(user=config.DB_USER,
                               password=config.DB_PASSWORD,
                               host=config.DB_HOST,
                               database=config.DB_NAME)
    cursor = mysql_connect.cursor()
    cursor.execute(query)
    all_rows = cursor.fetchall()
    row = all_rows[random.randint(0, len(all_rows)-1)]

    # Создаем клавиатуру с ответами и отправляем вместе с треком
    markup = generate_keyboard(row[2], row[3])
    bot.send_voice(message.chat.id, row[1], reply_markup=markup)

    # Включаем игровой режим
    set_user_game(message.chat.id, row[2])
    print(row)
    print(message)
    bot.send_message(message.chat.id, 'Как думаешь, {}, что за трек?'.format(message.from_user.first_name))

    mysql_connect.close()


'''@bot.message_handler(commands=['gm'])
def show_voice(message):
    print(message.text)
    my_message = bot.send_voice(message.chat.id, 'AwADAgADNAMAAnCn2EtrcElaYUnPKwI', None, timeout=50)
    bot.send_message(message.chat.id, my_message.voice.file_id, reply_to_message_id=my_message.message_id)'''

@bot.message_handler(func=lambda message: True, content_types=['text'])
def check_answer(message):

    # Если None, то человек не в игре
    answer = get_answer_for_user(message.chat.id)

    if not answer:
        #bot.send_message(message.chat.id, 'Чтобы начать игру, введите команду /gm')
        return
    else:
        # Убрать клавиатуру с вариантами ответа
        keyboard_hider = telebot.types.ReplyKeyboardRemove()
        # Если ответ правильный / неправильный
        if message.text == answer:
            #bot.send_message(message.chat.id, 'Верно!', reply_markup=keyboard_hider)
            bot.send_voice(message.chat.id, config.RIGHT_SOUND_FILE_ID, 'Верно!', reply_to_message_id=message.message_id)
        else:
            bot.send_message(message.chat.id, 'Неправильно, попробуй еще раз!', reply_markup=keyboard_hider, reply_to_message_id=message.message_id)

        finish_user_game(message.chat.id)

if __name__ == '__main__':
    bot.polling(none_stop=True)

# https://api.telegram.org/bot1870640059:AAHnqrAfdi2ZbuvTWeN0Xi2WONnYzQRwKzU/sendMessage?chat_id=514563949&text="aaa"
# https://api.telegram.org/bot1870640059:AAHnqrAfdi2ZbuvTWeN0Xi2WONnYzQRwKzU/setWebhook?url=https://959ca4522465.ngrok.io
import requests, telebot, time
from sqlalchemy.sql.functions import current_user

from config import BOT_TOKEN
from flask import Flask, request
from db_classes import db, Users, Groups, Sources, ug_relations

bot = telebot.TeleBot(BOT_TOKEN)
await_info = ''
current_user = ''

bot.remove_webhook()
time.sleep(1)
bot.set_webhook(url="https://f2e5340f0dbd.ngrok.io")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a really really really really long secret key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:postgres@localhost/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    groups = db.session.query(Groups).all()


@app.route('/', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    print("process_new_updates")
    return "ok", 200


@bot.message_handler(commands=['start'])
def handle_start(message):
    global current_user
    try:
        with app.app_context():
            all_users = db.session.query(Users).all()
        # Проверка на существование записи о таком пользователе
        for user in all_users:
            if message.from_user.username == user.username or message.chat.id == user.chat_id:
                current_user = user
                send_user_info(current_user)
                break
        else:
            # регистрация
            registration(message)
            send_user_info(current_user)
        # логика для авторизованных пользователей
        pass
    except Exception as e:
        print(e)


def registration(message):
    chat_id = message.chat.id
    global current_user
    current_user = Users(message.from_user.first_name, message.from_user.last_name, chat_id, message.from_user.username)


def send_user_info(user):
    s = f"{user.username}, проверь, пожалуйста, достоверность информации о себе: "
    s += '\r\n' * 2 + str(user)
    s += '\r\n' * 2 + 'Что добавим/изменим?'

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text='Фамилия', callback_data='surname'),
               telebot.types.InlineKeyboardButton(text='Имя', callback_data='name'))
    markup.add(telebot.types.InlineKeyboardButton(text='Отчество', callback_data='patronymic'),
               telebot.types.InlineKeyboardButton(text='Выбрать роль', callback_data='choose_role'))
    markup.add(telebot.types.InlineKeyboardButton(text='Все верно', callback_data='ok'))

    bot.send_message(user.chat_id, s, reply_markup=markup)


# def check_user_info_keyboard():
#     markup = telebot.types.InlineKeyboardMarkup()
#     markup.add(telebot.types.InlineKeyboardButton(text='Фамилия', callback_data='surname'),
#                telebot.types.InlineKeyboardButton(text='Имя', callback_data='name'))
#     markup.add(telebot.types.InlineKeyboardButton(text='Отчество', callback_data='patronymic'),
#                telebot.types.InlineKeyboardButton(text='Все верно', callback_data='ok'))
#     return markup


@bot.callback_query_handler(func=lambda call: True)
def edit_user_info(call):
    global current_user
    global await_info
    global groups

    if call.data == 'surname':
        await_info = 'surname'
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.send_message(current_user.chat_id, "Укажи фамилию")
    elif call.data == 'name':
        await_info = 'name'
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.send_message(current_user.chat_id, "Укажи имя")
    elif call.data == 'patronymic':
        await_info = 'patronymic'
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.send_message(current_user.chat_id, "Укажи отчество")
    elif call.data == 'choose_role':
        markup = telebot.types.InlineKeyboardMarkup()
        count = 0
        for g in groups:
            markup.add(telebot.types.InlineKeyboardButton(text=g.name, callback_data=str(count)))
            count += 1
        markup.add(telebot.types.InlineKeyboardButton(text='Выбрать все', callback_data='all'))
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.send_message(current_user.chat_id, "Выбери для себя роль", reply_markup=markup)
    elif call.data.isdigit() and int(call.data) in range(0,10):
        count = int(call.data)
        role = call.message.json['reply_markup']['inline_keyboard'][count][0]['text']
        for g in groups:
            if role == g.name:
                current_user.groups = []
                current_user.add_groups(g)
                # красивый вывод и подтверждение
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
                send_user_info(current_user)
                break
        else:
            bot.send_message(current_user.chat_id, "Такая роль отсутствует в БД")
    elif call.data == 'all':
        with app.app_context():
            groups = db.session.query(Groups)
        current_user.add_groups(groups)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        send_user_info(current_user)
    elif call.data == 'ok':
        await_info = ''
#       сохранение в бд
        save_user_to_db(current_user)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, 'Отлично! Изменениня сохранены!')


def save_user_to_db(user):
    try:
        with app.app_context():
            user_to_save = db.session.query(Users).filter_by(id=user.id,
                                                             username=user.username).first()
            if user_to_save:
                user_to_save.surname = user.surname
                user_to_save.name = user.name
                user_to_save.patronymic = user.patronymic
                user_to_save.chat_id = user.chat_id
                user_to_save.username = user.username
                user_to_save.active = user.active
                user_to_save.groups = []
                db.session.commit()
                user_to_save.add_groups(list(user.groups))
                pass
            else:
                db.session.add(user)
            db.session.commit()
    except Exception as e:
        print(e)


@bot.message_handler(content_types=['text'])
def handle_text(message):
    global current_user
    if await_info == 'surname':
        current_user.surname = message.text
        send_user_info(current_user)
    elif await_info == 'name':
        current_user.name = message.text
        send_user_info(current_user)
    elif await_info == 'patronymic':
        current_user.patronymic = message.text
        send_user_info(current_user)


if __name__ == "__main__":
    app.run()

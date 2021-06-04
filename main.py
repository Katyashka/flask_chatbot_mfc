import telebot, time
from sqlalchemy import create_engine

import fsm
from config import BOT_TOKEN
from flask import Flask, request
from db_classes import db, Users, Groups, fill_table
import dbworker

bot = telebot.TeleBot(BOT_TOKEN)
# await_info = ''

bot.remove_webhook()
time.sleep(1)
bot.set_webhook(url="https://d8df10750fbd.ngrok.io")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a really really really really long secret key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:postgres@localhost/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    table_names = engine.table_names()
    is_empty = table_names == []
    if is_empty:
        db.create_all()
        db.session.commit()
        fill_table(app)
    groups = db.session.query(Groups).all()
    all_users = db.session.query(Users).all()


@app.route('/', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200


@bot.message_handler(commands=['start', 'edit'])
def edit_user(message):
    try:
        # Проверка на существование записи о таком пользователе
        user = get_user(message.chat.id)
        if user is not None:
            send_user_info(user)
        else:
            # регистрация
            registration(message)
    except Exception as e:
        print(e)


def registration(message):
    chat_id = message.chat.id
    new_user = Users(chat_id, message.chat.username)
    save_user_to_db(new_user)


@bot.message_handler(commands=['registration'])
def handle_start(message):
    # регистрация
    registration(message)


def get_user(user_chat_id):
    for user in all_users:
        if user.chat_id == user_chat_id:
            return user
    return None


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


@bot.callback_query_handler(func=lambda call: call.data == 'surname')
def edit_user_surname(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Укажи фамилию")
    dbworker.set_state(call.message.chat.id, fsm.States.S_ENTER_SURNAME.value)


@bot.callback_query_handler(func=lambda call: call.data == 'name')
def edit_user_name(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Укажи имя")
    dbworker.set_state(call.message.chat.id, fsm.States.S_ENTER_NAME.value)


@bot.callback_query_handler(func=lambda call: call.data == 'patronymic')
def edit_user_patronymic(call):
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Укажи отчество")
    dbworker.set_state(call.message.chat.id, fsm.States.S_ENTER_PATRONYMIC.value)


@bot.callback_query_handler(func=lambda call: call.data == 'choose_role')
def edit_user_choose_role(call):
    markup = telebot.types.InlineKeyboardMarkup()
    count = 0
    for g in groups:
        markup.add(telebot.types.InlineKeyboardButton(text=g.name, callback_data=str(count)))
        count += 1
    markup.add(telebot.types.InlineKeyboardButton(text='Выбрать все', callback_data='all'))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Выбери для себя роль", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.isdigit() and int(call.data) in range(0,10))
def edit_user_role(call):
    count = int(call.data)
    role = call.message.json['reply_markup']['inline_keyboard'][count][0]['text']
    user = get_user(call.message.chat.id)
    for g in groups:
        if role == g.name:
            user.groups = []
            user.add_groups(g)
            save_user_to_db(user)
            # красивый вывод и подтверждение
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
            send_user_info(user)
            break
    else:
        bot.send_message(call.message.chat.id, "Такая роль отсутствует в БД")


@bot.callback_query_handler(func=lambda call: call.data == 'all')
def edit_user_all_role(call):
    user = get_user(call.message.chat.id)
    user.add_groups(groups)
    save_user_to_db(user)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    send_user_info(user)


@bot.callback_query_handler(func=lambda call: call.data == 'ok')
def edit_user_all_role(call):
    # сохранение в бд
    # save_user_to_db(current_user)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, 'Отлично! Редактирование завершено!')


def save_user_to_db(user):
    try:
        with app.app_context():
            db.session.add(user)
            db.session.commit()
            global all_users
            all_users = db.session.query(Users).all()
    except Exception as e:
        print(e)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == fsm.States.S_ENTER_SURNAME.value)
def user_entering_name(message):
    current_user = get_user(message.chat.id)
    current_user.surname = message.text
    save_user_to_db(current_user)
    send_user_info(current_user)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == fsm.States.S_ENTER_NAME.value)
def user_entering_name(message):
    current_user = get_user(message.chat.id)
    current_user.name = message.text
    save_user_to_db(current_user)
    send_user_info(current_user)


@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == fsm.States.S_ENTER_PATRONYMIC.value)
def user_entering_name(message):
    current_user = get_user(message.chat.id)
    current_user.patronymic = message.text
    save_user_to_db(current_user)
    send_user_info(current_user)


if __name__ == "__main__":
    app.run()

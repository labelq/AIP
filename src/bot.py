import telebot
from telebot import types
import json
from tinydb import TinyDB, Query
from poll.config import questions
from models.model import Anket

bot = telebot.TeleBot('YOUR_BOT_TOKEN')

user_data = {}
db = TinyDB('db.json')

def gen_markup(options, k):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    if options:
        l = [types.InlineKeyboardButton(x, callback_data='{"questionNumber": ' +
                                                         str(k) + ',"answerText": "' + x + '"}')
                                                         for x in options]
        markup.add(*l)
    return markup

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    req = call.data.split('_')
    print(req)
    json_string = json.loads(req[0])
    k = json_string['questionNumber'] + 1
    answer = json_string['answerText']
    if k == 0 and answer == "Нет, я боюся":
        k = -1
        return bot.edit_message_text(chat_id=call.message.chat.id,
                                     message_id=call.message.message_id,
                                     text='Ну и бойся дальше:(((')
    user_id = call.from_user.id
    if user_id not in user_data:
        user_data[user_id] = Anket(questions)
    anket = user_data[user_id]
    anket.add_answers(json_string)
    if k == anket.length:
        score = anket.get_score()
        del user_data[user_id]

        # Сохранение результатов в базу данных
        db.insert({'user_id': user_id, 'score': score, 'answers': anket.answers})
        print('Баллы: ', score)

        return bot.edit_message_text(chat_id=call.message.chat.id,
                                     message_id=call.message.message_id,
                                     text=f'Спасибо за уделённое время! \nЧтобы посмотреть свои результаты нажмите /results')

    button_column = anket.config[k].get('options')
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=anket.get_question(k),
                          reply_markup=gen_markup(button_column, k))

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = Anket(questions)
    anket = user_data[user_id]
    anket.reset_answers()
    db.remove(Query().user_id == user_id)  # Удаление предыдущих ответов пользователя из базы данных
    k = -1
    button_column = ['Погнали', 'Нет, я боюся']
    bot.send_message(chat_id=message.chat.id, text="Привет, я бот-абобус! \nОтветишь на мои вопросы?",
                     reply_markup=gen_markup(button_column, k))

@bot.message_handler(commands=['results'])
def show_results(message):
    user_id = message.from_user.id

    # Извлечение результатов опроса пользователя из базы данных
    results = db.search(Query().user_id == user_id)

    if results:
        # Отображение результатов опроса пользователю
        score = results[0]['score']
        answers = results[0]['answers']
        response = f"Ваши результаты опроса:\n\n"
        response += f"Баллы: {score}\n\n"
        for answer in answers:
            question_number = answer['questionNumber']
            question_text = questions[question_number]['text']
            user_answer = answer['answerText']
            response += f"{question_text}\nОтвет: {user_answer}\n\n"
    else:
        response = "У вас пока нет результатов опроса."

    bot.send_message(chat_id=message.chat.id, text=response)

bot.polling()

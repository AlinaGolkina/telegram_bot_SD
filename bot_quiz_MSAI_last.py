import random
import pandas as pd
from pony.orm import *

# будем использовать Pony ORM
db = Database()

# создаем entities БД для таблицы со статистикой и викториной
class Statistic(db.Entity):
    login = Required(str)
    correct = Required(int)
    wrong = Required(int)
    cur_subject = Required(str)
    
class Quiz(db.Entity):
    subject = Required(str)
    question = Required(str)
    answer1 = Required(str)
    answer2 = Required(str)
    answer3 = Required(str)
    answer4 = Required(str)
    correct = Required(str)

db.bind(provider='sqlite', filename=r'C:\Users\alina\database.sqlite11', create_db=True)

set_sql_debug(True)
db.generate_mapping(create_tables=True)

# Вопросы и ответы викторин взяты из источника https://baza-otvetov.ru/
quiz = pd.read_csv('quiz_total5.csv')
quiz = quiz.astype('str')
quiz.head()

# загружаем викторину в БД и делаем commit()
# for i, question in quiz.iterrows():
#    q = Quiz(question=question['question'], subject=question['Subject'], answer1=str(question['answer1']), answer2=str(question['answer2']), answer3=str(question['answer3']), answer4=str(question['answer4']), correct = str(question['Correct_answer'] ))
#    commit()

# создаем бота для игры - викторины
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from telegram import Poll, KeyboardButton, InlineKeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, CommandHandler, PollAnswerHandler, PollHandler, MessageHandler, CallbackContext, CallbackQueryHandler


def start(update: Update, context: CallbackContext) -> None:
    # Выводим приветствие с описанием команд бота
    update.message.reply_text(f"Привет, {update.message.chat.username} ! Это интелектуальная игра - викторина! Для выбора темы викторины, нажми /choose_subject, для продолжения викторины на выбранную тему жми /next, для просмотра статистики по ответам жми /statistic !  Удачи!")
    
    # Создаем настраиваемую клавиатуру с кнопками 
    button_list1 = [KeyboardButton("/start", callback_data='/start'),
                    KeyboardButton("/choose_subject", callback_data='/choose_subject'),
                    KeyboardButton("/help", callback_data='/help'),
                    KeyboardButton("/next", callback_data='/next'),
                    KeyboardButton("/statistic", callback_data='/statistic'),
                    KeyboardButton("/leaderboard", callback_data='/leaderboard')]
    # сборка клавиатуры из кнопок KeyboardButton
    reply_markup = ReplyKeyboardMarkup(build_menu(button_list1, n_cols=2), resize_keyboard=True)
    # отправка клавиатуры с кнопками команд в чат
    update.message.reply_text(text="Используйте кнопки на клавиатуре", reply_markup=reply_markup)
    # отправка клавиатуры для выбора тем в чат
    update.message.reply_text(text="Выберете тему для Quiz", reply_markup=buttons())

    
def buttons():
    
    # Готовим кнопки для кнопочного меню для выбора темы викторины
    button_list = [
    InlineKeyboardButton("Искусство", callback_data='Искусство'),
    InlineKeyboardButton("История", callback_data='История'),
    InlineKeyboardButton("Фильмы", callback_data='Фильмы'),
    InlineKeyboardButton("Окружающий мир", callback_data='Природа и животный мир'),
    InlineKeyboardButton("Спорт", callback_data='Спорт'),
    InlineKeyboardButton("География", callback_data='География'),
    InlineKeyboardButton("Литература", callback_data='Литература'),
    InlineKeyboardButton("Разное", callback_data='Разное'),
    InlineKeyboardButton("Наука", callback_data='Наука')]
    
    # сборка клавиатуры из кнопок `InlineKeyboardButton`
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=2), resize_keyboard=True)
    # отправка клавиатуры в чат
    return reply_markup

def choose_subject(update: Update, context: CallbackContext) -> None:
   
    # отправка клавиатуры для выбора темы викторины в чат'''
    update.message.reply_text(text="Выберете тему для Quiz", reply_markup=buttons())
  
                
def build_menu(buttons, n_cols,
               header_buttons=None,
               footer_buttons=None):
        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
        if header_buttons:
            menu.insert(0, [header_buttons])
        if footer_buttons:
            menu.append([footer_buttons])
        return menu    
    
def quiz_subject(update: Update, context: CallbackContext) -> None: #(update, _):

    # получаем выбранную пользователем тему для викторины
    query = update.callback_query
    variant = query.data

    query.edit_message_text(text=f"Выбранный вариант: {variant}")   
 
    # вытаскиваем из БД случайный вопрос на выбранную пользователем тему
    with db_session:
        q1 = select(q for q in Quiz if q.subject == variant)[:]
        q = select(q for q in Quiz if q.subject == variant)[:][random.randint(0,len(q1))]
        
    questions = [q.answer1, q.answer2, q.answer3, q.answer4]
    correct = q.correct
    correct_id = questions.index(correct)
    
    #  запускаем викторину
    message = update.effective_message.reply_poll(
        q.question, questions, type=Poll.QUIZ, correct_option_id=correct_id)
    
    # смотрим заведен ли это пользоватеь в таблицу БД со статистикой, если нет- то создаем его,
    # если заведен,  то обновляем его текущую выбранную тему
    with db_session:
            if len(select(q for q in Statistic if q.login == str(update.effective_chat.id))[:])==0:
                q = Statistic(login = str(update.effective_chat.id), cur_subject = variant, correct=0, wrong=0)
                commit()
            else:
                log = Statistic.get(login=str(update.effective_chat.id))
                log.cur_subject = variant
                
    # заводим информацию для дальнейшей обработки ответа
    payload = {"chat_id": update.effective_chat.id, "username":update.effective_chat.username}
    context.bot_data.update(payload)
    
    
def quiz_next(update: Update, context: CallbackContext) -> None: #(update, _):
    
    with db_session:
        if len(select(q for q in Statistic if q.login == str(context.bot_data['chat_id']))[:])==0:
            variant ='Разное'
        else:
            q = select(q for q in Statistic if q.login == str(context.bot_data['chat_id']))[:][0]
            variant = q.cur_subject
    # вытаскиваем случайный вопрос из БД
    with db_session:
        q1 = select(q for q in Quiz if q.subject == variant)[:]
        q = select(q for q in Quiz if q.subject == variant)[:][random.randint(0,len(q1))]
        
    questions = [q.answer1, q.answer2, q.answer3, q.answer4]
    correct = q.correct
    correct_id = questions.index(correct)
    
    # запускаем викторину
    message = update.effective_message.reply_poll(
        q.question, questions, type=Poll.QUIZ, correct_option_id=correct_id)
    
    # заводим информацию для дальнейшей обработки ответа
    payload = { "chat_id": update.effective_chat.id, "username": update.effective_chat.username}
    context.bot_data.update(payload)
    
    
def receive_quiz_answer(update: Update, context: CallbackContext) -> None:
    # Проверяем есть ли статистика по этому пользователю в БД, если нет, заводим
    
    
    with db_session:
        if len(select(q for q in Statistic if q.login == str(context.bot_data['username']))[:])==0:
            q = Statistic(login=str(context.bot_data['username']), cur_subject ='Разное', correct=0, wrong=0)
            commit()
    # id корректного варианта ответа
    correct = update.poll.correct_option_id
    # проверяем, ответил пользователь верно или нет, в зависимости от ответа обновляем его статистику в БД
    if update.poll.options[correct].voter_count == 1:
        with db_session:
            log = Statistic.get(login=str(context.bot_data['username']))
            log.correct+=1
    else:
        with db_session:
            log = Statistic.get(login=str(context.bot_data['username']))
            log.wrong+=1

def leaderboard(update: Update, context: CallbackContext):
    # выводим топ-5 игроков
    with db_session:
        q1 = select(q for q in Statistic).order_by(desc(Statistic.correct))[:]
    update.message.reply_text(
        f'Топ 5 игроков: \n\n { q1[0].login}: {q1[0].correct}/{q1[0].wrong},\n {q1[1].login}: {q1[1].correct}/{q1[1].wrong},\n{q1[2].login}: {q1[2].correct}/{q1[2].wrong},\n{q1[3].login}: {q1[3].correct}/{q1[3].wrong},\n{q1[4].login}: {q1[4].correct}/{q1[4].wrong}')
    
    
def stat(update: Update, context: CallbackContext):
    # Выводим статистику ответов пользователя
    with db_session:
        q1 = select(q for q in Statistic if q.login==str(update.message.chat['username']))[:][0]
    update.message.reply_text(f'Статистика ответов: \n\n Правильных ответов: {q1.correct} \n Неправильных ответов:  {q1.wrong}')
        
def message(update: Update, context: CallbackContext):
    # если пользователь ввел некорректную команду, выводим сообщение
    update.message.reply_text("Вы ввели некорректную команду. Используйте команду /start, /next, /choose_subject для продолжения игры или выберите кнопки меню")
        
def help_handler(update: Update, context: CallbackContext) -> None:
    # выводим сообщение при нажатии /help
    update.message.reply_text("Выберите /choose_subject для выбора темы викторины, /next для продолжения викторины на выбранную тему, /statistics для простмотра статистики по ответам, /help если нужна помощь")
    

def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater("5232503148:AAHmq4oa0MvjInmvIC-Vn477_-D2GQx7VLg")
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CallbackQueryHandler(quiz_subject))
    dispatcher.add_handler(CommandHandler('help', help_handler))
    dispatcher.add_handler(CommandHandler('next', quiz_next))
    dispatcher.add_handler(PollHandler(receive_quiz_answer))
    dispatcher.add_handler(CommandHandler('choose_subject', choose_subject))
    dispatcher.add_handler(CommandHandler('statistic', stat))
    dispatcher.add_handler(CommandHandler('leaderboard', leaderboard))
    dispatcher.add_handler(MessageHandler(Filters.text,message))
    # Запуск бота
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
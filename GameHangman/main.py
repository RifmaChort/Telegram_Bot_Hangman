#7125253698:AAGN1SW98a34ZYdzVap8vtOB4QXZAee5Y9E
import logging
import random
import atexit
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Словари с темами и словами для разных уровней сложности
easy_themes = {
    'Животные': [
        {'word': 'кот', 'hint': 'Домашнее животное', 'fact': 'Коты могут спать до 16 часов в день.'},
        {'word': 'пес', 'hint': 'Друг человека', 'fact': 'Собаки являются самыми верными животными.'},
    ],
    'Фрукты': [
        {'word': 'лимон', 'hint': 'Кислый фрукт', 'fact': 'Лимоны содержат много витамина С.'},
        {'word': 'слива', 'hint': 'Фиолетовый фрукт', 'fact': 'Сливы бывают разных цветов и вкусов.'},
    ],
}

medium_themes = {
    'Животные': [
        {'word': 'кенгуру', 'hint': 'Прыгающее животное из Австралии',
         'fact': 'Кенгуру могут прыгать на высоту до 3 метров.'},
        {'word': 'носорог', 'hint': 'Животное с рогом', 'fact': 'Носороги могут весить до 3 тонн.'},
    ],
    'Фрукты': [
        {'word': 'гранат', 'hint': 'Красный плод с семенами', 'fact': 'Гранаты богаты антиоксидантами.'},
        {'word': 'манго', 'hint': 'Тропический фрукт', 'fact': 'Манго является национальным плодом Индии.'},
    ],
}

hard_themes = {
    'Животные': [
        {'word': 'хохлатый пингвин', 'hint': 'Птица из Антарктиды',
         'fact': 'Хохлатые пингвины известны своим ярким оперением на голове.'},
        {'word': 'вомбат', 'hint': 'Животное, роющее норы',
         'fact': 'Вомбаты - это сумчатые млекопитающие из Австралии.'},
    ],
    'Фрукты': [
        {'word': 'питахайя', 'hint': 'Фрукт с ярко-розовой кожурой',
         'fact': 'Питахайя также известна как "драконовый фрукт".'},
        {'word': 'карасау', 'hint': 'Редкий фрукт из Южной Америки',
         'fact': 'Карасау имеет сладкий и кисловатый вкус.'},
    ],
}

MAX_ATTEMPTS = 6

# Глобальные переменные для хранения состояния игры
game_data = {}
current_message_id = {}  # Хранение ID текущего сообщения для каждого пользователя


def start(update: Update, _: CallbackContext) -> None:
    chat_id = update.message.chat_id

    # Удаляем предыдущее сообщение, если оно существует
    if chat_id in current_message_id:
        try:
            _.bot.delete_message(chat_id=chat_id, message_id=current_message_id[chat_id])
        except:
            pass
        # Удаляем текущую игровую сессию, если существует
        if chat_id in game_data:
            del game_data[chat_id]

    keyboard = [
        [InlineKeyboardButton("Начать", callback_data='start_game')],
        [InlineKeyboardButton("Как играть", callback_data='how_to_play')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = update.message.reply_text('Добро пожаловать в игру "Виселица"!', reply_markup=reply_markup)

    current_message_id[chat_id] = message.message_id  # Сохраняем ID сообщения


def button(update: Update, _: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id

    # Обновляем текущее сообщение
    current_message_id[chat_id] = query.message.message_id
    query.answer()

    if query.data == 'start_game':
        if chat_id in game_data:
            query.edit_message_text(text="Игра уже начата. Пожалуйста, завершите текущую игру перед началом новой.")
            return
        choose_difficulty(query)
    elif query.data == 'how_to_play':
        show_instructions(query)
    elif query.data.startswith('difficulty_'):
        level = query.data.split('_')[1]
        game_data[chat_id] = {'difficulty': level, 'guessed_letters': set()}
        choose_theme(query, level)
    elif query.data.startswith('theme_'):
        start_game(update, _)
    elif query.data == 'play_again':
        game_data.pop(chat_id, None)  # Безопасное удаление ключа
        choose_difficulty(query)


def choose_difficulty(query):
    keyboard = [
        [InlineKeyboardButton("Легко", callback_data='difficulty_easy')],
        [InlineKeyboardButton("Средне", callback_data='difficulty_medium')],
        [InlineKeyboardButton("Сложно", callback_data='difficulty_hard')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Выберите уровень сложности:", reply_markup=reply_markup)


def choose_theme(query, level):
    themes = get_themes_by_difficulty(level)
    keyboard = [[InlineKeyboardButton(theme, callback_data=f'theme_{theme}')] for theme in themes.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Выберите тему:", reply_markup=reply_markup)


def show_instructions(query):
    keyboard = [
        [InlineKeyboardButton("Начать", callback_data='start_game')],
        [InlineKeyboardButton("Как играть", callback_data='how_to_play')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    instructions = (
        "Инструкции по игре 'Виселица':\n"
        "1. Выберите тему.\n"
        "2. Пытайтесь угадать слово, нажимая на буквы.\n"
        "3. Вы можете использовать подсказку для открытия буквы.\n"
        "4. Если вы угадаете слово, вы победите!\n"
        "5. Если сделаете слишком много неверных попыток, вы проиграете."
    )
    query.edit_message_text(text=instructions, reply_markup=reply_markup)


def start_game(update: Update, _: CallbackContext) -> None:
    query = update.callback_query
    theme = query.data.split('_')[1]
    chat_id = query.message.chat_id
    level = game_data[chat_id]['difficulty']
    themes = get_themes_by_difficulty(level)

    word_data = random.choice(themes[theme])
    word = word_data['word']
    hint = word_data['hint']
    fact = word_data['fact']

    max_hints = 1 if level in ['easy', 'medium'] else 2

    game_data[chat_id].update({
        'word': word,
        'hint': hint,
        'fact': fact,
        'attempts': 0,
        'incorrect_guesses': 0,
        'max_attempts': MAX_ATTEMPTS,
        'masked_word': '_' * len(word),
        'hint_used': 0,  # Количество использованных подсказок
        'max_hints': max_hints  # Максимальное количество подсказок
    })

    show_game_state(query, chat_id)


def get_themes_by_difficulty(level):
    if level == 'easy':
        return easy_themes
    elif level == 'medium':
        return medium_themes
    elif level == 'hard':
        return hard_themes


def show_game_state(query, chat_id):
    game = game_data[chat_id]
    masked_word = ' '.join(game['masked_word'])
    hangman_stage = get_hangman_stage(game['incorrect_guesses'])
    keyboard = []

    # Разделяем буквы на строки по 8 букв
    alphabet = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    row_length = 8
    for i in range(0, len(alphabet), row_length):
        row = [InlineKeyboardButton(letter, callback_data=f'guess_{letter}') if letter not in game[
            'guessed_letters'] else InlineKeyboardButton(' ', callback_data='disabled') for letter in
               alphabet[i:i + row_length]]
        keyboard.append(row)

    if game['incorrect_guesses'] < game['max_attempts'] and game['hint_used'] < game['max_hints']:
        keyboard.append([InlineKeyboardButton("Подсказка", callback_data='use_hint')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text=f"{hangman_stage}\n<b>Слово:</b> {masked_word}\nПодсказка: {game['hint']}\nОсталось попыток: {game['max_attempts'] - game['incorrect_guesses']}",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


def get_hangman_stage(incorrect_guesses):
    stages = [
        '',
        'Этап 1',
        'Этап 2',
        'Этап 3',
        'Этап 4',
        'Этап 5',
        'Этап 6'
    ]
    return stages[incorrect_guesses]


def handle_guess(update: Update, _: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    game = game_data[chat_id]

    letter = query.data.split('_')[1]

    if letter in game['guessed_letters']:
        return  # Игнорируем повторное нажатие на уже угаданную букву

    game['guessed_letters'].add(letter)

    if letter in game['word']:
        masked_word_list = list(game['masked_word'])
        for i, l in enumerate(game['word']):
            if l == letter:
                masked_word_list[i] = letter
        game['masked_word'] = ''.join(masked_word_list)
    else:
        game['incorrect_guesses'] += 1

    if game['masked_word'] == game['word']:
        query.edit_message_text(
            text=f"Поздравляем! Вы угадали слово: {game['word']}\nФакт: {game['fact']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать заново", callback_data='play_again')]])
        )
        game_data.pop(chat_id, None)  # Безопасное удаление ключа
    elif game['incorrect_guesses'] >= game['max_attempts']:
        query.edit_message_text(
            text=f"Игра окончена! Загаданное слово: {game['word']}\nФакт: {game['fact']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать заново", callback_data='play_again')]])
        )
        game_data.pop(chat_id, None)  # Безопасное удаление ключа
    else:
        show_game_state(query, chat_id)
        time.sleep(0.3)  # Блокировка нажатия на 0.3 секунды


def use_hint(update: Update, _: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    game = game_data[chat_id]

    if game['hint_used'] >= game['max_hints']:
        return

    available_indices = [i for i, l in enumerate(game['word']) if game['masked_word'][i] == '_']
    if available_indices:
        index = random.choice(available_indices)
        letter = game['word'][index]
        game['guessed_letters'].add(letter)
        masked_word_list = list(game['masked_word'])
        masked_word_list[index] = letter
        game['masked_word'] = ''.join(masked_word_list)

    game['hint_used'] += 1

    if game['masked_word'] == game['word']:
        query.edit_message_text(
            text=f"Поздравляем! Вы угадали слово: {game['word']}\nФакт: {game['fact']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать заново", callback_data='play_again')]])
        )
        game_data.pop(chat_id, None)  # Безопасное удаление ключа
    else:
        show_game_state(query, chat_id)
        time.sleep(0.3)  # Блокировка нажатия на 0.3 секунды


def clear_chat(context: CallbackContext) -> None:
    for chat_id in current_message_id.keys():
        message_id = current_message_id[chat_id]
        for message_id in range(message_id, message_id - 100, -1):  # Попытка удалить последние 100 сообщений
            try:
                context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                continue


def cleanup(updater):
    logger.info("Очистка чата перед завершением работы.")
    clear_chat(updater.job_queue._dispatcher)


def main() -> None:
    updater = Updater("7125253698:AAGN1SW98a34ZYdzVap8vtOB4QXZAee5Y9E")

    # Установка команды для отображения в меню
    updater.bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
        BotCommand("clear", "Очистить чат")
    ])

    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("clear", lambda update, context: clear_chat(context)))
    updater.dispatcher.add_handler(CallbackQueryHandler(button, pattern='^start_game$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(button, pattern='^how_to_play$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(button, pattern='^difficulty_'))
    updater.dispatcher.add_handler(CallbackQueryHandler(button, pattern='^theme_'))
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_guess, pattern='^guess_'))
    updater.dispatcher.add_handler(CallbackQueryHandler(use_hint, pattern='^use_hint$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(button, pattern='^play_again$'))

    # Регистрация функции очистки перед завершением работы
    atexit.register(cleanup, updater)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()



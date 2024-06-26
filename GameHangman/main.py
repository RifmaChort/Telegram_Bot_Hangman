#7125253698:AAGN1SW98a34ZYdzVap8vtOB4QXZAee5Y9E
import logging
import random
import json
import atexit
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ParseMode, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
from pathlib import Path

# Исправленный формат логгера
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def load_themes(filename):
    """Загрузка данных из файлов"""
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)


easy_themes = load_themes('easy_themes.json')
medium_themes = load_themes('medium_themes.json')
hard_themes = load_themes('hard_themes.json')

MAX_ATTEMPTS = 6

# Глобальные переменные для хранения состояния игры
game_data = {}
current_message_id = {}  # Хранение ID текущего сообщения для каждого пользователя


def start(update: Update, context: CallbackContext) -> None:
    logger.info("Функция start вызвана")
    chat_id = update.message.chat_id

    # Удаляем предыдущее сообщение, если оно существует
    if chat_id in current_message_id:
        try:
            context.bot.delete_message(chat_id=chat_id, message_id=current_message_id[chat_id])
            logger.info(f"Сообщение {current_message_id[chat_id]} удалено")
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения {current_message_id[chat_id]}: {e}")
        # Удаляем текущую игровую сессию, если существует
        if chat_id in game_data:
            del game_data[chat_id]

    keyboard = [
        [InlineKeyboardButton("Начать", callback_data='start_game')],
        [InlineKeyboardButton("Как играть 📜", callback_data='how_to_play')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = update.message.reply_text('Добро пожаловать в игру "Виселица"!', reply_markup=reply_markup)

    current_message_id[chat_id] = message.message_id  # Сохраняем ID сообщения
    logger.info(f"Новое сообщение {message.message_id} сохранено")


def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id

    query.answer()
    logger.info(f"Функция button вызвана с callback_data: {query.data}")

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
        start_game(update, context, query)
    elif query.data == 'play_again':
        game_data.pop(chat_id, None)  # Безопасное удаление ключа
        clear_previous_messages(chat_id, context)
        # Вызов команды /start через создание объекта Update
        update.message = query.message  # Присваивание сообщения query.message
        start(update, context)


def choose_difficulty(query):
    logger.info("Функция choose_difficulty вызвана")
    keyboard = [
        [InlineKeyboardButton("Легко", callback_data='difficulty_easy')],
        [InlineKeyboardButton("Средне", callback_data='difficulty_medium')],
        [InlineKeyboardButton("Сложно", callback_data='difficulty_hard')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Выберите уровень сложности:", reply_markup=reply_markup)


def choose_theme(query, level):
    logger.info(f"Функция choose_theme вызвана с уровнем сложности: {level}")
    themes = get_themes_by_difficulty(level)
    keyboard = [[InlineKeyboardButton(theme, callback_data=f'theme_{theme}')] for theme in themes.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Выберите тему:", reply_markup=reply_markup)


def show_instructions(query):
    logger.info("Функция show_instructions вызвана")
    keyboard = [
        [InlineKeyboardButton("Начать", callback_data='start_game')],
        [InlineKeyboardButton("Как играть 📜", callback_data='how_to_play')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    instructions = (
        "Инструкции по игре 'Виселица':\n"
        "1. Выберите уровень сложности.\n"
        "2. Выберите тему.\n"
        "3. Пытайтесь угадать слово, нажимая на буквы.\n"
        "4. Вы можете использовать подсказку для открытия буквы 💡.\n"
        "5. Если вы угадаете слово, вы победите 🎉!\n"
        "6. Если сделаете слишком много неверных попыток, вы проиграете 😔."
    )
    query.edit_message_text(text=instructions, reply_markup=reply_markup)


def start_game(update: Update, context: CallbackContext, query) -> None:
    logger.info("Функция start_game вызвана")
    theme = query.data.split('_')[1]
    chat_id = query.message.chat_id
    level = game_data[chat_id]['difficulty']
    themes = get_themes_by_difficulty(level)

    logger.info("clear_previous_messages вызвана")
    clear_previous_messages(chat_id, context)  # Удалить все предыдущие сообщения

    word_data = random.choice(themes[theme])
    word = word_data['word']
    hint = random.choice(word_data['hints'])
    fact = random.choice(word_data['facts'])

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
        'max_hints': max_hints,  # Максимальное количество подсказок
        'message_id': None  # Сохраняем ID сообщения с игрой
    })

    send_initial_game_state(query, chat_id, context)


def get_themes_by_difficulty(level):
    logger.info(f"Функция get_themes_by_difficulty вызвана с уровнем сложности: {level}")
    if level == 'easy':
        return easy_themes
    elif level == 'medium':
        return medium_themes
    elif level == 'hard':
        return hard_themes


def send_initial_game_state(query, chat_id, context):
    logger.info("Функция send_initial_game_state вызвана")
    game = game_data[chat_id]
    masked_word = ' '.join(game['masked_word'])
    hangman_stage = get_hangman_stage(game['incorrect_guesses'])
    keyboard = generate_keyboard(game)

    reply_markup = InlineKeyboardMarkup(keyboard)
    image_path = Path(f'images/image{game["incorrect_guesses"]}.jpg')

    # Создаем новое сообщение
    message = context.bot.send_photo(
        chat_id=chat_id,
        photo=open(image_path, 'rb'),
        caption=f"{hangman_stage}\n<b>Слово:</b> {masked_word}\nПодсказка: {game['hint']}\nОсталось попыток: {game['max_attempts'] - game['incorrect_guesses']}",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    game['message_id'] = message.message_id
    logger.info(f"Новое сообщение {message.message_id} с состоянием игры отправлено")


def show_game_state(query, chat_id):
    logger.info("Функция show_game_state вызвана")
    game = game_data[chat_id]
    masked_word = ' '.join(game['masked_word'])
    hangman_stage = get_hangman_stage(game['incorrect_guesses'])
    keyboard = generate_keyboard(game)

    reply_markup = InlineKeyboardMarkup(keyboard)

    image_path = Path(f'images/image{game["incorrect_guesses"]}.jpg')

    query.message.bot.edit_message_media(
        chat_id=chat_id,
        message_id=game['message_id'],
        media=InputMediaPhoto(open(image_path, 'rb')),
        reply_markup=reply_markup
    )
    query.message.bot.edit_message_caption(
        chat_id=chat_id,
        message_id=game['message_id'],
        caption=f"{hangman_stage}\n<b>Слово:</b> {masked_word}\nПодсказка: {game['hint']}\nОсталось попыток: {game['max_attempts'] - game['incorrect_guesses']}",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


def get_hangman_stage(incorrect_guesses):
    logger.info("Функция get_hangman_stage вызвана")
    return f"Этап {incorrect_guesses + 1}"


def handle_guess(update: Update, context: CallbackContext) -> None:
    logger.info("Функция handle_guess вызвана")
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
        query.message.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=game['message_id'],
            caption=f"Поздравляем! Вы угадали слово: {game['word']} 🎉\nФакт: {game['fact']}",
            parse_mode=ParseMode.HTML
        )
        # Добавляем новое сообщение с кнопкой "Начать снова"
        context.bot.send_message(
            chat_id=chat_id,
            text="Игра окончена! Хотите сыграть снова?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать снова 🔄", callback_data='play_again')]])
        )
        game_data.pop(chat_id, None)  # Безопасное удаление ключа
    elif game['incorrect_guesses'] >= game['max_attempts']:
        # Показать последнее изображение виселицы
        show_game_state(query, chat_id)
        time.sleep(0.5)  # Дать время на отображение последнего изображения

        query.message.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=game['message_id'],
            caption=f"Игра окончена! Загаданное слово: {game['word']} 😔\nФакт: {game['fact']}",
            parse_mode=ParseMode.HTML
        )
        # Добавляем новое сообщение с кнопкой "Начать снова"
        context.bot.send_message(
            chat_id=chat_id,
            text="Игра окончена! Хотите сыграть снова?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать снова 🔄", callback_data='play_again')]])
        )
        game_data.pop(chat_id, None)  # Безопасное удаление ключа
    else:
        show_game_state(query, chat_id)
        time.sleep(0.3)  # Блокировка нажатия на 0.3 секунды


def use_hint(update: Update, context: CallbackContext) -> None:
    logger.info("Функция use_hint вызвана")
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
        query.message.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=game['message_id'],
            caption=f"Поздравляем! Вы угадали слово: {game['word']} 🎉\nФакт: {game['fact']}",
            parse_mode=ParseMode.HTML
        )
        # Добавляем новое сообщение с кнопкой "Начать снова"
        context.bot.send_message(
            chat_id=chat_id,
            text="Игра окончена! Хотите сыграть снова?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать снова 🔄", callback_data='play_again')]])
        )
        game_data.pop(chat_id, None)  # Безопасное удаление ключа
    else:
        show_game_state(query, chat_id)
        time.sleep(0.3)  # Блокировка нажатия на 0.3 секунды


def generate_keyboard(game):
    logger.info("Функция generate_keyboard вызвана")
    keyboard = []
    alphabet = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    row_length = 8
    for i in range(0, len(alphabet), row_length):
        row = [InlineKeyboardButton(letter, callback_data=f'guess_{letter}') if letter not in game[
            'guessed_letters'] else InlineKeyboardButton(' ', callback_data='disabled') for letter in
               alphabet[i:i + row_length]]
        keyboard.append(row)

    if game['incorrect_guesses'] < game['max_attempts'] and game['hint_used'] < game['max_hints']:
        keyboard.append([InlineKeyboardButton("Открыть букву", callback_data='use_hint')])

    return keyboard


def clear_previous_messages(chat_id, context):
    logger.info(f"Вызвана функция clear_previous_messages для чата {chat_id}")
    if chat_id in current_message_id:
        for message_id in range(current_message_id[chat_id], current_message_id[chat_id] - 10, -1):  # Попытка удалить последние 10 сообщений
            try:
                context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                logger.info(f"Сообщение {message_id} удалено")
            except Exception as e:
                logger.error(f"Не удалось удалить сообщение {message_id}: {e}")
                continue


def clear_chat(context: CallbackContext) -> None:
    logger.info("Вызвана функция clear_chat")
    for chat_id in current_message_id.keys():
        clear_previous_messages(chat_id, context)


def cleanup(updater):
    logger.info("Очистка чата перед завершением работы.")
    clear_chat(updater.job_queue._dispatcher)


def main() -> None:
    logger.info("Запуск бота")
    updater = Updater("7125253698:AAGN1SW98a34ZYdzVap8vtOB4QXZAee5Y9E")

    # Установка команды для отображения в меню
    updater.bot.set_my_commands([
        BotCommand("start", "Запустить бота")
    ])

    updater.dispatcher.add_handler(CommandHandler("start", start))
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

import requests
import telegram

SEND_PHOTO = 'Send your photo 📷 and I will add beautiful filters to it\n⛲️ 🌃 🌄'
WAIT_A_SECOND = 'Wait a second, please 🕐'
FILTERS_EMOJI = {
    'Sunny': '🌤',
    'Msqrd': '🎭',
    'Marquet': '🌃',
    'Rafael': '👀',
    'Piranese': '🏛',
    'Milk': '🍼',
    'Girl': '👧🏽',
    'Ra': '🌅',
    'Fire': '🔥'
}

VINCI_PRELOAD = 'http://vinci.camera/preload'
VINCI_PROCESS = 'http://vinci.camera/process/{}/{}'

all_filters = requests.get('http://vinci.camera/list').json()
filters = []
for data in all_filters:
    if data['name'] in FILTERS_EMOJI:
        filters.append({
            'name': data['name'],
            'emoji': FILTERS_EMOJI[data['name']],
            'id': data['id']
        })


def register(bot):
    bot.handlers['vinci-upload-image'] = upload_image
    bot.handlers['vinci-results-view'] = results_view
    bot.handlers['vinci-results-iteration'] = results_iteration


def upload_image(message, bot):
    bot.user_set(message.u_id, 'next_handler', 'vinci-results-view')
    bot.send_message(message.u_id, SEND_PHOTO)


def results_view(message, bot):
    if not message.photo:
        bot.call_handler(message, 'vinci-upload-image')
        return
    bot.user_set(message.u_id, 'next_handler', 'vinci-results-iteration')
    bot.telegram.send_message(message.u_id, WAIT_A_SECOND)
    bot.telegram.sendChatAction(message.u_id, 'upload_photo')
    file_id = message.photo[-1].file_id
    photo = bot.telegram.getFile(file_id)
    bot.logger.info('Photo for Vinci url: {}'.format(photo.file_path))
    content = requests.get(photo.file_path).content
    response = requests.post(VINCI_PRELOAD, files={
        'file': ('photo.jpg', content)
    }).json()
    bot.user_set(message.u_id, 'vinci:photo_id', response['preload'])
    bot.logger.info('Vinci photo id: {}'.format(response['preload']))
    bot.user_set(message.u_id, 'vinci:current_filter', 0)
    bot.telegram.send_photo(message.u_id, photo=VINCI_PROCESS.format(
        response['preload'], filters[0]['id']
    ))
    bot.telegram.send_message(message.u_id, filters[0]['name'] + ' ' + filters[0]['emoji'],
                              reply_markup=build_results_keyboard(0, message, bot))


def results_iteration(message, bot):
    if 'menu' in message.text:
        bot.call_handler(message, 'main-menu')
        return
    if message.photo:
        bot.call_handler(message, 'vinci-results-view')
        return
    bot.user_set(message.u_id, 'next_handler', 'vinci-results-iteration')
    bot.telegram.sendChatAction(message.u_id, 'upload_photo')
    for (i, filter_data) in enumerate(filters):
        if filter_data['name'] in message.text:
            filter_num = i
            new_filter = filter_data
            break
    else:
        if '⏮' in message.text:
            filter_num = int(bot.user_get(message.u_id, 'vinci:previous_filter'))
            new_filter = filters[filter_num]
        else:
            filter_num = int(bot.user_get(message.u_id, 'vinci:next_filter'))
            new_filter = filters[filter_num]
    photo_id = bot.user_get(message.u_id, 'vinci:photo_id')
    bot.telegram.send_photo(message.u_id, photo=VINCI_PROCESS.format(
        photo_id, new_filter['id']
    ))
    bot.telegram.send_message(message.u_id, new_filter['name'] + ' ' + new_filter['emoji'],
                              reply_markup=build_results_keyboard(filter_num, message, bot))


def build_results_keyboard(filter_num, message, bot):
    keyboard = []
    # Next and back buttons
    previous_filter = (filter_num - 1) % len(filters)
    next_filter = (filter_num + 1) % len(filters)
    bot.user_set(message.u_id, 'vinci:previous_filter', previous_filter)
    bot.user_set(message.u_id, 'vinci:next_filter', next_filter)
    back_button = '⏮ {}'.format(filters[previous_filter]['name'])
    next_button = '{} ⏭'.format(filters[next_filter]['name'])
    keyboard.append([back_button, next_button])
    # Menu buttons
    keyboard.append(['Back to menu 🏠'])
    # All filters buttons
    filters_per_row = 3
    current_row = []
    for filter_data in filters:
        if len(current_row) == filters_per_row:
            keyboard.append(current_row)
            current_row = []
        current_row.append(filter_data['name'] + ' ' + filter_data['emoji'])
    if current_row:
        keyboard.append(current_row)
    return telegram.ReplyKeyboardMarkup(keyboard)

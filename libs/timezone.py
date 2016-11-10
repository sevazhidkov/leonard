import json
import arrow


def local_time(bot, u_id):
    user_location = bot.user_get(u_id, 'location')
    if user_location:
        location = json.loads(user_location)
        time = arrow.utcnow().to(location['timezone'])
        return time

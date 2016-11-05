import json
import arrow


def local_time(bot, u_id):
    location = json.loads(bot.user_get(u_id, 'location'))
    time = arrow.utcnow().to(location['timezone'])
    return time

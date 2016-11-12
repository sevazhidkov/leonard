import os
import string
import random
import hashlib
import falcon
import redis

ALPHABET = string.ascii_letters + string.digits
SHORT_LINK_FORMAT = "{}/l/".format(os.environ['WEBHOOK_HOSTNAME'])

redis_client = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))


class GetLinkResource:
    def on_get(self, req, resp, query):
        base_key = 'core:shrt:link:{}:'.format(query)
        full_link = redis_client.get(base_key + 'url')
        if full_link is None:
            raise falcon.HTTPMovedPermanently('http://sheldon.ai/')
        redis_client.incr(base_key + 'visits')
        user_hash = redis_client.get(base_key + 'user')
        print('Uber user hash:', user_hash)
        resp.status = '301 Moved Permanently'
        if user_hash:
            print('setting cookie in uber')
            resp.set_header('Set-Cookie', 'user={}'.format(user_hash.decode('utf-8')))
            # resp.set_cookie('user', user_hash.decode('utf-8'), max_age=60 * 60 * 24)
        resp.set_header('Location', full_link.decode('utf-8'))
        print(resp._headers)


def short_user_link(u_id, link, code_size=11):
    # Generate hash for user
    sha_hash = hashlib.sha256()
    sha_hash.update(str(u_id).encode())
    sha_hash.update(os.environ['BOT_SECRET'].encode())
    user_hash = sha_hash.hexdigest()
    user_hash_key = 'core:shrt:hash:{}'.format(user_hash)
    redis_client.set(user_hash_key, u_id)

    # Save link
    unique = False
    while not unique:
        code = ''
        for _ in range(code_size):
            code += random.choice(ALPHABET)
        link_key = 'core:shrt:link:{}:url'.format(code)
        if not redis_client.exists(link):
            unique = True
    redis_client.set(link_key, link)

    link_hash_key = 'core:shrt:link:{}:user'.format(code)
    redis_client.set(link_hash_key, user_hash)

    return SHORT_LINK_FORMAT + code

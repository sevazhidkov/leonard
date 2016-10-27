import os
import string
import random
import hashlib
import redis
from flask import make_response, redirect, request

ALPHABET = string.ascii_letters + string.digits
SHORT_LINK_FORMAT = "{}/l/".format(os.environ['WEBHOOK_HOSTNAME'])

redis_client = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))


def get_link_route(query):
    base_key = 'core:shrt:link:{}:'.format(query)
    full_link = redis_client.get(base_key + 'url')
    if full_link is None:
        return redirect('http://sheldon.ai/')
    redis_client.incr(base_key + 'visits')
    response = make_response(redirect(full_link))
    user_hash = redis_client.get(base_key + 'user')
    if user_hash:
        response.set_cookie('user', user_hash)
    return response


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

import jinja2

WELCOME_MESSSAGE_TEMPLATE = jinja2.Template("""Hello{% if first_name %}, {{first_name}}{% endif %} 👋

Welcome abroad! My name is Leonard and I can help you with your everyday tasks:

🍝 find a perfect restaurant,
🚕 get a Uber car,
📰 read news on your favourite websites
and much more...""")


def register(bot):
    bot.handlers['welcome-message'] = welcome_message


def welcome_message(message, bot):
    bot.telegram.send_message(
        chat_id=message.from_user.id,
        text=WELCOME_MESSSAGE_TEMPLATE.render(first_name=message.from_user.first_name)
    )

import jinja2

WELCOME_MESSSAGE_TEMPLATE = jinja2.Template("""Hi{% if first_name %}, {{first_name}}{% endif %} 👋""")
INTRODUCTION_MESSAGE = "My name is Leonard. I was created to help you with your everyday tasks ✌️"

WELCOME_SETUP_RESULT = ("Thanks 👌\n\nNow we're ready to go, enjoy using the bot 🤖")
CONTACT_WITH = ("📖 If you have any problems or suggestions, you can contact "
                "directly with Leonard Bot developer @sevazhidkov")


def register(bot):
    bot.handlers['welcome-message'] = welcome_message
    bot.handlers['welcome-setup-result'] = welcome_setup_result


def welcome_message(message, bot):
    bot.telegram.send_message(
        chat_id=message.u_id,
        text=WELCOME_MESSSAGE_TEMPLATE.render(first_name=message.from_user.first_name)
    )
    bot.telegram.send_message(message.u_id, INTRODUCTION_MESSAGE)
    message.handler = 'registration-started'
    bot.call_handler(message, 'subscriptions-setup')


def welcome_setup_result(message, bot):
    bot.user_set(message.u_id, 'registered', '1')
    bot.telegram.send_message(message.u_id, WELCOME_SETUP_RESULT)
    bot.telegram.send_message(message.u_id, CONTACT_WITH)
    message.handler = 'registration-finished'
    bot.call_handler(message, 'main-menu')

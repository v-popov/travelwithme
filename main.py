import logging
import json
from urllib.request import urlopen
import os
from telegram import Update, InputFile, TelegramObject
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler

# https://docs.python-telegram-bot.org/en/v20.0a1/telegram.ext.filters.html
# https://core.telegram.org/bots/api
# mount volume

token = os.environ['tg_token']
admin_chat_id = os.environ['admin_chat_id']

path = os.environ['path']

username_to_chat_id_filename = 'username_to_chat_id.json'
username_to_chat_id = {}
groups = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def init():
    if username_to_chat_id_filename not in os.listdir():
        print('Creating new username_to_chat_id')
        with open(username_to_chat_id_filename, 'w', encoding='utf-8') as file:
            dummy_dict = {"test": 123}
            json.dump(dummy_dict, file, ensure_ascii=False)


def update_username_to_chat_id(new_username_to_chat_id):
    global username_to_chat_id
    print(f"Updating {username_to_chat_id} with new values: {new_username_to_chat_id}")
    username_to_chat_id.update(new_username_to_chat_id)
    print(f"Result: {username_to_chat_id}")
    with open(username_to_chat_id_filename, 'r+') as file:
        json.dump(username_to_chat_id, file, ensure_ascii=False)


def add_username_to_chat_id_entry(username, chat_id):
    global username_to_chat_id
    username_to_chat_id[username] = chat_id
    init()
    with open(username_to_chat_id_filename, 'r+') as file:
        file_data = json.load(file)
        file_data.update({username: chat_id})
        file.seek(0)
        json.dump(file_data, file, ensure_ascii=False)


async def start(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"1 UPDATE: {update}\n")
    #username_to_chat_id[update.effective_chat.username] = update.effective_chat.id
    add_username_to_chat_id_entry(update.effective_chat.username, update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! If somebody has told you, that they will be sharing photos with you using this bot, then no further action is needed - you'll receive it as soon as the sender sends them. If you want to set up your own list of recepients, please go to the contacts you want to share you photos/videos with and share those contacts with the bot.")
    await context.bot.send_message(chat_id=admin_chat_id, text=update['message']['chat'])


async def _add_contact(update: Update, context: 'ContextTypes.DEFAULT_TYPE', to_user):
    from_user = update['message']['from']['id']
    print(from_user, to_user)
    if from_user not in groups:
        groups[from_user] = []
    if to_user not in groups[from_user]:
        groups[from_user].append(to_user)
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Registered')


async def contact(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"2 UPDATE: {update}\n")
    to_user = update['message']['contact']['user_id']
    await _add_contact(update, context, to_user)


async def contact_url(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"3 UPDATE: {update}\n")
    to_user = update['message']['text'].split('/')[-1]
    await _add_contact(update, context, to_user)


async def add(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"4 UPDATE: {update}\n")
    to_user = update['message']['text'].replace('/add @', '').strip()
    to_user = username_to_chat_id[to_user]
    await _add_contact(update, context, to_user)


async def list_registered_contacts(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"5 UPDATE: {update}\n")
    from_user = update.effective_chat.id
    if from_user in groups:
        registered_contacts_txt = '; '.join(groups[from_user])
    else:
        registered_contacts_txt = 'No contacts registered yet'
    print(f"registered_contacts_txt: {registered_contacts_txt}")
    await context.bot.send_message(chat_id=from_user, text=registered_contacts_txt)


async def echo(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f'6 UPDATE: {update}')
    from_user = update['message']['from']['id']
    if from_user in groups:
        for to_user in groups[from_user]:
            print(f'Sending from user {from_user} to user {to_user}')
            try:
                await context.bot.forward_message(chat_id=to_user, from_chat_id=update['message']['from']['id'], message_id=update['message']['message_id'])
            except:
                try:
                    await context.bot.forward_message(chat_id=username_to_chat_id[to_user], from_chat_id=update['message']['from']['id'], message_id=update['message']['message_id'])
                except:
                    await context.bot.send_message(chat_id=admin_chat_id, text=f"Unable send message to {to_user}")



async def backup(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"7 UPDATE: {update}\n")
    with open(username_to_chat_id_filename, 'rb') as file:
        q = InputFile(obj=file, filename=f"attach://{path}/username_to_chat_id.json", attach=True)
        await context.bot.send_document(chat_id=admin_chat_id, document=q)


async def download(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"8 UPDATE: {update}\n")
    print(f'update.effective_chat.id: {update.effective_chat.id}; admin_chat_id: {admin_chat_id}')
    if str(update.effective_chat.id) == str(admin_chat_id):
        print('Downloading')
        # check for sender id
        # file = await context.bot.get_file(update.message.document)#.download()
        # writing to a custom file
        with open(f"{path}/username_to_chat_id.json", 'wb') as f:
            file = await context.bot.get_file(update.message.document)
            print(f"file: {file}")
            q = await file.download(out=f)
            new_username_to_chat_id = json.loads(urlopen(file['file_path']).read().decode("utf-8"))
            print(f"q: {q}")
            print(f"new_username_to_chat_id: {type(new_username_to_chat_id)}; {new_username_to_chat_id}")
            update_username_to_chat_id(new_username_to_chat_id)


# unique AgAD9h0AA66BSQ
# file_id BQACAgIAAxkBAAN1Yq-w6cKdqJRhUoyAzSp8wFGZ-DcAAvYdAAOugUni7NAC-w3-nygE


if __name__ == '__main__':
    init()

    application = ApplicationBuilder().token(token).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    add_handler = CommandHandler('add', add)
    application.add_handler(add_handler)

    backup_handler = CommandHandler(command='backup', callback=backup)  # , filters=filters.Chat(chat_id=admin_chat_id)
    application.add_handler(backup_handler)

    list_handler = CommandHandler('list', list_registered_contacts)
    application.add_handler(list_handler)

    contact_handler = MessageHandler(filters.CONTACT, contact)
    application.add_handler(contact_handler)

    contact_handler_url = MessageHandler(filters.TEXT & (filters.Entity('url') | filters.Entity('text_link')), contact_url)
    application.add_handler(contact_handler_url)

    echo_handler = MessageHandler(filters.PHOTO | filters.VIDEO, echo)
    application.add_handler(echo_handler)

    download_handler = MessageHandler(filters.Document.FileExtension('json'), download)
    application.add_handler(download_handler)

    application.run_polling()
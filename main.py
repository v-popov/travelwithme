import logging
import json
from urllib.request import urlopen
import os
from telegram import Update, InputFile
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler

# https://docs.python-telegram-bot.org/en/v20.0a1/telegram.ext.filters.html
# https://core.telegram.org/bots/api
# mount volume

token = os.environ['tg_token']
admin_chat_id = int(os.environ['admin_chat_id'])

path = os.environ['project_path']

username_to_chat_id_filename = 'username_to_chat_id.json'
groups_filename = 'groups.json'
username_to_chat_id = {}
groups = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def update_dict(d_current, new_records):
    d_current.update(new_records)
    return d_current


def save_dict_to_json(d, filepath):
    print(f"Saving {filepath}")
    with open(filepath, 'w', encoding='utf-8') as file:
        json.dump(d, file, ensure_ascii=False)


def update_dict_from_json(dict_to_update, filepath):
    with open(filepath, 'r+') as file:
        file_data = json.load(file)
        dict_to_update.update(file_data)
        return dict_to_update


def init():
    print(os.listdir(path))
    if username_to_chat_id_filename not in os.listdir(path):
        print('Creating new username_to_chat_id')
        save_dict_to_json({"test": 123}, f"{path}/{username_to_chat_id_filename}")
    if groups_filename not in os.listdir(path):
        print('Creating new groups')
        save_dict_to_json({"test": []}, f"{path}/{groups_filename}")


def update_username_to_chat_id(new_username_to_chat_id):
    global username_to_chat_id
    print(f"Updating {username_to_chat_id} with new values: {new_username_to_chat_id}")
    username_to_chat_id.update(new_username_to_chat_id)
    print(f"Result: {username_to_chat_id}")
    save_dict_to_json(username_to_chat_id, f"{path}/{username_to_chat_id_filename}")
    # with open(username_to_chat_id_filename, 'r+') as file:
    #     json.dump(username_to_chat_id, file, ensure_ascii=False)


def update_groups(new_groups):
    global groups
    print(f"Updating {groups} with new values: {new_groups}")
    groups.update(new_groups)
    print(f"Result: {groups}")
    save_dict_to_json(groups, f"{path}/{groups_filename}")


def add_username_to_chat_id_entry(username, chat_id):
    global username_to_chat_id
    username = str(username)
    username_to_chat_id[username] = chat_id
    init()
    with open(username_to_chat_id_filename, 'r+') as file:
        file_data = json.load(file)
        file_data.update({username: chat_id})
        file.seek(0)
        json.dump(file_data, file, ensure_ascii=False)


def get_name(contact):
    name = ''
    try:
        name += contact.first_name + ' '
    except:
        pass
    try:
        name += contact.last_name + ' '
    except:
        pass
    try:
        name += contact.phone_number + ' '
    except:
        pass
    return name


async def start(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"1 UPDATE: {update}\n")
    add_username_to_chat_id_entry(update.effective_chat.username, update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! If somebody has told you, that they will be sharing photos with you using this bot, then no further action is needed - you'll receive it as soon as the sender sends them. If you want to set up your own list of recepients, please go to the contacts you want to share you photos/videos with and share those contacts with the bot.")
    await context.bot.send_message(chat_id=admin_chat_id, text=update['message']['chat'])


async def _add_contact(update: Update, context: 'ContextTypes.DEFAULT_TYPE', to_user, name):
    global groups
    from_user = str(update['message']['from']['id'])
    to_user = str(to_user)
    print(from_user, to_user)
    if from_user not in groups:
        groups[from_user] = {'chat_ids': [], 'names': []}
    if to_user not in groups[from_user]['chat_ids']:
        groups[from_user]['chat_ids'].append(to_user)
        groups[from_user]['names'].append(name)
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Registered')


async def contact(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"2 UPDATE: {update}\n")
    contact = update['message']['contact']
    to_user = contact['user_id']
    name = get_name(contact)
    await _add_contact(update, context, to_user, name)


async def contact_url(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"3 UPDATE: {update}\n")
    to_user = update['message']['text'].split('/')[-1]
    await _add_contact(update, context, to_user, to_user)


async def delete(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    global groups
    print(f"3.5 UPDATE: {update}\n")
    from_user = str(update['message']['from']['id'])
    msg_text = update['message']['text']
    msg_text = msg_text.replace('/delete', '')
    print(f'msg_text: {msg_text}')
    if msg_text == '':
        await context.bot.send_message(chat_id=from_user, text=f"To remove a contact from the bot, send /list command to bot, then pick a number corresponding to the contact you want to delete and send /delete command followed by that number. E.g., /delete 2")
    elif from_user in groups:
        try:
            number_to_delete = int(msg_text)
            if number_to_delete < 1 or number_to_delete > len(groups[from_user]['chat_ids']):
                await context.bot.send_message(chat_id=from_user,
                                               text=f"Unable to delete user - incorrect value: {msg_text}")
            else:
                groups[from_user]['chat_ids'].pop(number_to_delete-1)
                deleted_name = groups[from_user]['names'].pop(number_to_delete-1)
                await context.bot.send_message(chat_id=from_user,
                                               text=f"Successfully deleted: {deleted_name}")
        except:
            await context.bot.send_message(chat_id=from_user, text=f"Unable to delete user - incorrect value: {msg_text}")
    else:
        await context.bot.send_message(chat_id=from_user, text=f"No contacts registered yet")


async def list_registered_contacts(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"5 UPDATE: {update}\n")
    from_user = f"{update.effective_chat.id}"
    print(f"Groups: {groups}")
    if (from_user in groups) and (len(groups[from_user]['names']) > 0):
        registered_contacts_txt = ''
        for i, name in enumerate(groups[from_user]['names'], start=1):
            registered_contacts_txt += f"{i}) {name};\n"
    else:
        registered_contacts_txt = 'No contacts registered yet'
    print(f"registered_contacts_txt: {registered_contacts_txt}")
    await context.bot.send_message(chat_id=from_user, text=registered_contacts_txt)


async def echo(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f'6 UPDATE: {update}')
    from_user = str(update['message']['from']['id'])
    if from_user in groups:
        for to_user in groups[from_user]['chat_ids']:
            print(f'Sending from user {from_user} to user {to_user}')
            try:
                await context.bot.forward_message(chat_id=to_user, from_chat_id=update['message']['from']['id'], message_id=update['message']['message_id'])
            except:
                try:
                    await context.bot.forward_message(chat_id=username_to_chat_id[to_user], from_chat_id=update['message']['from']['id'], message_id=update['message']['message_id'])
                except:
                    await context.bot.send_message(chat_id=admin_chat_id, text=f"Unable send message to {to_user}")


async def send_json(context, filepath):
    with open(filepath, 'rb') as file:
        q = InputFile(obj=file, filename=f"attach://{filepath}", attach=True)
        await context.bot.send_document(chat_id=admin_chat_id, document=q)


async def backup(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"7 UPDATE: {update}\n")
    save_dict_to_json(username_to_chat_id, f"{path}/{username_to_chat_id_filename}")
    await send_json(context, f"{path}/{username_to_chat_id_filename}")

    save_dict_to_json(groups, f"{path}/{groups_filename}")
    await send_json(context, f"{path}/{groups_filename}")


async def download(update: Update, context: 'ContextTypes.DEFAULT_TYPE'):
    print(f"8 UPDATE: {update}\n")
    #if str(update.effective_chat.id) == str(admin_chat_id):
    print('Downloading')
    document = update.message.document
    filename = document['file_name']
    print(f"document = {document}")
    with open(f"{path}/{filename =}", 'wb') as f:
        file = await context.bot.get_file(document)
        print(f"file: {file}")
        await file.download(out=f)
        new_file = json.loads(urlopen(file['file_path']).read().decode("utf-8"))
        print(f"new_file: {new_file}")
        if filename == groups_filename:
            update_groups(new_file)
        elif filename == username_to_chat_id_filename:
            update_username_to_chat_id(new_file)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Unrecognized filename: {filename}")
        #update_username_to_chat_id(new_username_to_chat_id)


if __name__ == '__main__':
    init()

    application = ApplicationBuilder().token(token).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    delete_handler = CommandHandler('delete', delete)
    application.add_handler(delete_handler)

    backup_handler = CommandHandler(command='backup', callback=backup, filters=filters.Chat(chat_id=admin_chat_id))
    application.add_handler(backup_handler)

    list_handler = CommandHandler('list', list_registered_contacts)
    application.add_handler(list_handler)

    contact_handler = MessageHandler(filters.CONTACT, contact)
    application.add_handler(contact_handler)

    contact_handler_url = MessageHandler(filters.TEXT & (filters.Entity('url') | filters.Entity('text_link')), contact_url)
    application.add_handler(contact_handler_url)

    echo_handler = MessageHandler(filters.PHOTO | filters.VIDEO, echo)
    application.add_handler(echo_handler)

    download_handler = MessageHandler(filters.Chat(chat_id=admin_chat_id) | filters.Document.FileExtension('json'), download)
    application.add_handler(download_handler)

    application.run_polling()
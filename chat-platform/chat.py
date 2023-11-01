#!/usr/bin/python3
from flask import Flask, render_template, request, url_for
from datetime import datetime
import csv
import os
import logging
import json

logging.basicConfig(filename='chat.log', level=logging.DEBUG, encoding='utf-8')

app = Flask(__name__)
CHAT_FOLDER = 'chats'


def log_chats_dict():
    pass

def chat_save_path(fromUser, toUser):
    users = sorted([fromUser, toUser])
    return f'{CHAT_FOLDER}/{users[0]}-{users[1]}.csv'

def get_chat(fromUser, toUser):
    path = chat_save_path(fromUser, toUser)
    if not os.path.exists(path):
        return []

    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)
  
def add_message(fromUser, toUser, chatID, content):
    path = chat_save_path(fromUser, toUser)
    with open(path, 'a', newline='') as csvfile:
        fieldnames = ['sender', 'content', 'date']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if csvfile.tell() == 0:
            writer.writeheader()
        writer.writerow({'sender': fromUser, 
                        'content': content, 
                        'date': datetime.now().strftime('%a, %b %d, %Y @ %I:%M%p')})
    log_chats_dict()

def string_to_color(string):
    colors = ['#FF007F', '#9BC63B', '#0D8ABC',
              '#BF360C', '#330E62', '#124116', 
              '#00695c', '#121858', '#5d4030']
    return colors[(abs(hash(string.lower())) % 9)].replace("#", "")

@app.route('/messages', methods=['GET', 'POST'])
def message():
    fromUser = request.args.get('fromUser')    
    toUser = request.args.get('toUser')
    if not fromUser or not toUser:
        return f"Missing fromUser or toUser in /messages (fromUser={fromUser}, toUser={toUser})", 400
    chatID = f"{toUser}-{fromUser}"
    if request.method == 'POST':
        content = request.values.get('message_to_send')
        add_message(fromUser, toUser, chatID, content)
    log_chats_dict()
    return render_template('messages-chat.html', 
                           toUser_color=string_to_color(fromUser),
                           toUser=toUser, 
                           fromUser=fromUser, 
                           chatID=chatID,
                           chats=get_chat(fromUser, toUser),
                           lenSideUsers=0)

@app.route('/chat', methods=['GET', 'POST'])
def message_chat():
    fromUser = request.args.get('fromUser')
    toUser = request.args.get('toUser')
    if not fromUser or not toUser:
        return f"Missing fromUser or toUser in /chat (fromUser={fromUser}, toUser={toUser})", 400
    chatID = f"{toUser}-{fromUser}"
    if request.method == 'POST':
        content = request.values.get('message_to_send')
        add_message(fromUser, toUser, chatID, content)
        
    return render_template('blocks/messages.html',
                           messages=get_chat(fromUser, toUser), 
                           toUser_color=string_to_color(toUser),
                           fromUser_color=string_to_color(fromUser),
                           toUser=toUser,
                           fromUser=fromUser,
                           chatID=chatID)

@app.route('/', methods=['GET'])
def all_chats():
    files = os.listdir(CHAT_FOLDER)
    files_path = [os.path.join(CHAT_FOLDER, basename) for basename in files]
    latest_files = sorted(files_path, key=os.path.getctime, reverse=True)

    chat_list = []
    for file in latest_files:
        fromUser, toUser = os.path.splitext(os.path.basename(file))[0].split('-')
        chat_link = url_for('message', fromUser=fromUser, toUser=toUser)

        # add values to dictionary
        chat_item = {
            'fromUser': fromUser,
            'toUser': toUser,
            'chat_link': chat_link,
            'chat_id': f"{fromUser}-{toUser}"
        }

        chat_list.append(chat_item)

    return render_template('all-chats.html', 
                           chat_list=chat_list)


if __name__ == '__main__':
    if not os.path.exists(CHAT_FOLDER):
        os.makedirs(CHAT_FOLDER)
    app.run(host='0.0.0.0', debug=True, use_reloader=True, port=3000)
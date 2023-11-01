# Chat Platform (Part of AI-Persona-Chat)

AI-Persona-Chat Platform is a barebones chat platform allowing two users to chat. It provides APIs to ping messages between simulated users and browse through historical chats.

## Table of Contents

- [Chat Platform (Part of AI-Persona-Chat)](#chat-platform-part-of-ai-persona-chat)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Developer Documentation](#developer-documentation)
  - [User Documentation](#user-documentation)
  - [FAQs](#faqs)

## <a name="installation">Installation</a>

Clone the repository

```bash
git clone https://github.com/bearlike/AI-Persona-Chat.git
```

Navigate to the chat-platform directory in the AI-Persona-Chat folder

```bash
cd AI-Persona-Chat/chat-platform
```

(Optional: Recommended) It's better to set up a virtual enviornment before installing dependencies.

```bash
python3 -m venv chat_env
source chat_env/bin/activate # On Linux/Mac
```

Install dependencies

```bash
pip install -r requirements.txt
```

## <a name="developer-doc">Developer Documentation</a>

The chat-platform operates on a Flask Web Server. The main file is `chat.py`. 

Upon startup, the Flask app looks at `chats/` folder, and loads up every CSV file. The filename of each CSV file should be `User1-User2.csv` format, where User1 and User2 are chat participants. The User1 and User2 does not maintain any order.

There are mainly two routes that you need to be aware of:

* `/messages`: The main chatting endpoint. This endpoint is used to both GET and POST chat messages.

    To render previous chats and to send new chats, `/messages` uses GET parameters to identify participants of the chat: `/messages?fromUser=User1&toUser=User2`.

    Here, `fromUser` parameter is sender of the message and `toUser` is the recipient.

    During a POST request, the message from input (form `message_to_send`) would be saved as a message from `fromUser` to `toUser`.

* `/`: Starting endpoint. GET requests to `/` displays all existing chats that are currently stored in `/chats/`. Every chat would be displayed as a link leading to the respective chat on `/messages`.

Behind the scenes, every chat is stored as a CSV file located at `chats/` with filename as `User1-User2.csv`, where User1 and User2 are participants.

## <a name="user-doc">User Documentation</a>

Start the Flask app:

```bash
python chat.py
```

Now, you can go to `localhost:3000` in your browser to view all the active chats. You can click on any chat to start chatting.

The URL `http://localhost:3000/messages?fromUser=User1&toUser=User2` represents a chat between User1 and User2.

To send a chat, you can type your message in the Chat Input box and press the Send button.

The chat room can hold more than one message, and every message will be saved even if you navigate away from the chat room or close the tab.

## <a name="faqs">FAQs</a>

**Q: I am getting error related to no module found while starting the Server. What should I do?**

A: Make sure you have installed the necessary modules. Run `pip install -r requirements.txt` again and make sure you see no errors during installation.

**Q: I am being unable to send/receive messages. Why?**

A: Ensure that you are using correct endpoint for a chat: `/messages?fromUser=User1&toUser=User2` (replace User1 and User2 with respective usernames).
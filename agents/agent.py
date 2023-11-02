#!/usr/bin/env python3

import json
import openai
import os
from collections import defaultdict
import jinja2
from time import sleep
import requests
from pprint import pprint
import logging
from dotenv import load_dotenv
import datetime
import pickle
import urllib.parse
import pyperclip


# log into a file
logging.basicConfig(filename='agent.log', level=logging.INFO)
# Load environment variables from .env
load_dotenv()

def ai_agent_factory():
    return {
        "name": None,
        "persona": None,
        "intent": None, 
    }

# Determine which model to use 
MODEL_MODE = os.getenv("MODEL_MODE", "openai")
if MODEL_MODE == "openai":
    openai.api_key = os.getenv("OPENAI_API_KEY", None)
    openai.organization = os.getenv("OPENAI_ORD_ID", None)
    MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-16k")

# Configure OpenAI package to point to our custom API endpoint
#   running llama-2-13b.Q5_K_S model
elif MODEL_MODE == "llama" or MODEL_MODE == "serge":
    openai.api_base = os.getenv("LLAMA_API_SERVER", None)
    openai.api_key = os.getenv("LLAMA_API_KEY", None)
    MODEL = os.getenv("LLAMA_MODEL", "Facebook-LLaMA2-13B")

elif MODEL_MODE == "manual":
    MODEL="Facebook-LLaMA2-13B"

# Raise exception if invalid MODEL_MODE is provided
else:
    raise Exception("Invalid MODEL_MODE")

# Global variables
AI_AGENTS = defaultdict(ai_agent_factory)
TURNS = None
CURRENT_TURN = None
CONVERSATION_LOG = []

# Jinja2 template setup
TEMPLATE_LOADER = jinja2.FileSystemLoader(searchpath="./prompt_templates/")
TEMPLATE_ENV = jinja2.Environment(loader=TEMPLATE_LOADER)
TEMPLATE_FILE = "chat_completion.txt.j2"

# UI setup
UI_URL = "http://localhost:3000"

# Generate human readable timestamp
STORE_TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
IS_COMPLETED = False


# Read the index.json file and return the list of personas
def get_personas_list():
    with open("personas/index.json") as f:
        personas = json.load(f)
    return personas


# Read the persona file and return the text
def get_persona_text(persona_path):
    with open(persona_path) as f:
        persona_text = f.read()
    return persona_text


# Ask user to select a persona from the list.
def select_persona(bot_index=None) -> None:
    global AI_AGENTS
    if bot_index is None or type(bot_index) is not int:
        # Bot must have an int index
        raise Exception("Bot index must be an int")
    personas = get_personas_list()
    print(f"\nPlease choose a personality for Agent { bot_index }:")
    for i, p in enumerate(personas):
        print(f"{i + 1}: {p['personality_name']}")
    persona_index = int(input("\nEnter a number: ")) - 1
    print(f"Agent { bot_index } is assigned as '{personas[persona_index]['personality_name']}'")
    persona_text = get_persona_text(personas[persona_index]['path'])
    # Storing metadata in the AI_AGENTS dict
    AI_AGENTS[bot_index]["persona"] = persona_text
    AI_AGENTS[bot_index]["name"] = personas[persona_index]['personality_name']
    # Get intent of the persona from the user
    intent = input("What is the intent of this persona? (leave empty for default) - ").strip()
    if intent is None or intent == "":
        intent = personas[persona_index]["intent"]
        print(f"Using default intent for this persona - `{intent}`")
    AI_AGENTS[bot_index]["intent"] = intent
    logging.info(f"Agent { bot_index } is assigned as '{ str(AI_AGENTS[bot_index]) }'")


def compile_prompt(
                    bot_index=None, 
                    converation_history=CONVERSATION_LOG
                ) -> str:
    if bot_index is None or type(bot_index) is not int:
        # Bot must have an int index
        raise Exception("Bot index must be an int")
    template = TEMPLATE_ENV.get_template(TEMPLATE_FILE)
    # Render the template
    prompt = template.render(
        personality_description=AI_AGENTS[bot_index]["persona"],
        conversation_history=converation_history,
        intent=AI_AGENTS[bot_index]["intent"],
        number_of_turns_left=TURNS - CURRENT_TURN,
        is_new_conversation=True if CURRENT_TURN == 1 else False,
    )
    return prompt


def get_prompt(bot_index=None) -> str:
    global CURRENT_TURN
    if bot_index is None or type(bot_index) is not int:
        # Bot must have an int index
        raise Exception("Bot index must be an int")
    if CURRENT_TURN == 0:
        # First turn
        other_bot_index = 2 if bot_index == 1 else 1
        other_bot_name = AI_AGENTS[other_bot_index]["name"]
        converation_history = [
            f"There is no conversation history yet. You are starting a new conversation with { other_bot_name }."
        ]
    else:
        converation_history = CONVERSATION_LOG
    CURRENT_TURN += 1
    compiled_prompt = compile_prompt(
        bot_index=bot_index, 
        converation_history=converation_history
    )
    # Store latest compiled prompt as a text file in chat_logs directory for each bot_index
    directory = os.path.join("chat_logs", MODEL)
    os.makedirs(directory, exist_ok=True)
    filename = os.path.join(directory, f"latest_prompt_{str(bot_index)}.txt")
    with open(filename, "w") as f:
        f.write(compiled_prompt)
    return compiled_prompt


def inital_setup():
    global TURNS
    global CURRENT_TURN
    print("Note: Agent 1 always starts the conversation.")
    for bot_idx in range(1, 3):
        select_persona(bot_index=bot_idx)
    # Get number of turns from the user
    TURNS = int(input("\nHow many conversational turns? (example: 10) - "))
    if TURNS <= 1:
        raise Exception("Number of turns must be greater than 1")
    CURRENT_TURN = 0
    user1, user2 = AI_AGENTS[1]["name"], AI_AGENTS[2]["name"]
    chat_url = f"{UI_URL}/messages?fromUser={user1.replace(' ', '%20')}&toUser={user2.replace(' ', '%20')}"
    print(f"Please open { chat_url } in your browser to see the conversation.")
    print("Press Enter to start the conversation.....")
    input()


def send_chat_request_to_ui(from_User, to_User, message) -> None:
    global CURRENT_TURN
    # if CURRENT_TURN == 1:
    #     return
    url = f"{UI_URL}/api/chat?fromUser={from_User.replace(' ', '%20')}&toUser={to_User.replace(' ', '%20')}"
    # Send a POST request to the UI
    # Wait until OK response is received
    response = requests.post(url, data={"message_to_send": message})
    if response.status_code == 200:
        logging.info(f"Message sent to UI: { message }, 200 OK")
    else:
        logging.error(f"Message sent to UI: { message }, { response.status_code }")
    # sleep(2)


def get_llm_response(prompt):
    global MODEL
    if_loop = True
    retry_count = 0
    print("[ ", end="")
    temperature = 0.8
    while if_loop and retry_count < 3:
        try:
            retry_count += 1
            print("Generating, ", end="")
            if MODEL_MODE == "serge" and MODEL == "Facebook-LLaMA2-13B":
                # Using Serge API
                # Get conversation id
                requests_url = f"{openai.api_base}/api/chat/?model={MODEL}&temperature={temperature}&top_k=50&top_p=0.95&max_length=4000&context_window=4000&gpu_layers=48&repeat_last_n=64&repeat_penalty=1.3&init_prompt=Below%20is%20an%20instruction%20that%20describes%20a%20task.%20Write%20a%20response%20that%20appropriately%20completes%20the%20request.&n_threads=11"
                response = requests.post(requests_url)
                conv_id = response.text.strip().replace('"', "")
                logging.info(f"Conversation ID: { conv_id }")
                # URL-safe encode the prompt
                prompt = urllib.parse.quote(prompt)
                # Get response
                requests_url = f"{openai.api_base}/api/chat/{conv_id}/question?prompt={prompt}"
                logging.info(f"Request URL: { requests_url }")
                response = requests.post(requests_url)
                completion = json.loads(response.text)
                print("\n\n")
                pprint(completion)
                top_answer = completion["choices"][0]["text"].strip()
            elif MODEL_MODE == "manual":
                # For models that do not have a public API
                pyperclip.copy(prompt)
                print("Prompt copied to clipboard.")
                # Get response from user
                completion = None
                top_answer = input("Enter response: ")
            elif MODEL_MODE == "openai" or MODEL_MODE == "llama":
                completion = openai.ChatCompletion.create(
                    model=MODEL, 
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
                top_answer = completion["choices"][0]["message"]["content"].strip()
            print("Generated, Validating, ", end="")
            try:
                top_answer = json.loads(top_answer)["dialogue"]
            except json.JSONDecodeError:
                logging.error(f"Retrying since error in parsing the response as JSON - { top_answer }")
                print("Retrying (JSON Error), ", end="")
                continue
            if_loop = False
            print("Success ]")
            del completion
            return top_answer
        except openai.error.ServiceUnavailableError:
            print("Retrying (Service Unavailable), ", end="")
            time_sleep_unit = (2 ** retry_count) - 1
            logging.error(f"Service Unavailable.Sleeping for { time_sleep_unit } seconds")
            sleep(time_sleep_unit)  # exponential backoff
    _error_text = f"Unable to get appropriate response from { MODEL } model. Check logs."
    raise Exception(_error_text)


def store_conversation_log():
    global CONVERSATION_LOG
    global STORE_TIMESTAMP    
    # Create chat log directory if it doesn't exist
    directory = os.path.join("chat_logs", MODEL)
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, f"chat_log_{STORE_TIMESTAMP}.txt")
    # Write the conversation log to a file
    with open(filepath, "w") as f:
        f.write("\n".join(CONVERSATION_LOG))
    print(f"Conversation log written to `{ filepath }`")


def cache_necessary_data(save=True, load=False) -> bool:
    """ The OpenAI Python package is quite slow and buggy.
        So we cache the necessary data to a file and load it
        when the program timed out or restarted.
        This function is used to save/load the cache.
        Set to `save` by default.
    Args:
        save (bool, optional): Defaults to True.
        load (bool, optional): Defaults to False.

    Returns:
        bool: _description_
    """
    global MODEL_MODE
    global MODEL
    global AI_AGENTS
    global TURNS
    global CURRENT_TURN
    global CONVERSATION_LOG
    global STORE_TIMESTAMP
    global IS_COMPLETED
    cache_dir = os.path.join(".cache")
    cache_filepath = os.path.join(cache_dir, "agents_cache.pkl")
    if save:
        # Pickle the conversation log
        os.makedirs(cache_dir, exist_ok=True)
        # Store MODEL_MODE, MODEL, AI_AGENTS, TURNS, CURRENT_TURN, CONVERSATION_LOG, STORE_TIMESTAMP, IS_COMPLETED in a dict
        cache_dict = {
            "MODEL_MODE": MODEL_MODE,
            "MODEL": MODEL,
            "AI_AGENTS": AI_AGENTS,
            "TURNS": TURNS,
            "CURRENT_TURN": CURRENT_TURN,
            "CONVERSATION_LOG": CONVERSATION_LOG,
            "STORE_TIMESTAMP": STORE_TIMESTAMP,
            "IS_COMPLETED": IS_COMPLETED,
        }
        with open(cache_filepath, "wb") as f:
            pickle.dump(cache_dict, f)
        print(f"Cache written to `{ cache_filepath }`")
        return True
    elif load and os.path.exists(cache_filepath):
        # Load the conversation log
        with open(cache_filepath, "rb") as f:
            cache_dict = pickle.load(f)

        if not cache_dict["IS_COMPLETED"]:
            print(f"Incomplete conversation found in cache using `{ cache_dict['MODEL'] }`")
            pprint(cache_dict["CONVERSATION_LOG"])
            print("Should we continue? (y/n) - ", end="")
            user_input = input()
            if user_input.lower() == "y":
                print("Loading cache....")
            else:
                return False
        else:
            return False
        IS_COMPLETED = cache_dict["IS_COMPLETED"]
        CONVERSATION_LOG = cache_dict["CONVERSATION_LOG"]
        MODEL_MODE = cache_dict["MODEL_MODE"]
        MODEL = cache_dict["MODEL"]
        AI_AGENTS = cache_dict["AI_AGENTS"]
        TURNS = cache_dict["TURNS"]
        CURRENT_TURN = cache_dict["CURRENT_TURN"]
        CONVERSATION_LOG = cache_dict["CONVERSATION_LOG"]
        STORE_TIMESTAMP = cache_dict["STORE_TIMESTAMP"]
        print(f"Cache loaded from `{ cache_filepath }`")
        return True


def conversation_loop():
    global CURRENT_TURN
    global IS_COMPLETED
    print("Entering conversation loop. Press Ctrl+C to exit.")
    while CURRENT_TURN < TURNS + 1:
        print(f"Running Turn: { CURRENT_TURN } out of { TURNS } -", end="")
        single_conversation()
        sleep(2)
    IS_COMPLETED = True


def single_conversation():
    global CURRENT_TURN
    current_bot_index = CURRENT_TURN % 2 + 1
    prompt = get_prompt(bot_index=current_bot_index)
    response = get_llm_response(prompt)
    # Check if response ends with [END_OF_CONVERSATION]
    if response.endswith("[END_OF_CONVERSATION]"):
        print(f"Conversation ended due to [END_OF_CONVERSATION] by Agent #{ current_bot_index }")
        response = response.replace("[END_OF_CONVERSATION]", "")
        CURRENT_TURN = TURNS + 2
    # Get current bot name
    current_bot_name = AI_AGENTS[current_bot_index]["name"]
    CONVERSATION_LOG.append(f"{current_bot_name}: {response}")
    # Get other bot name
    other_bot_index = 2 if current_bot_index == 1 else 1
    other_bot_name = AI_AGENTS[other_bot_index]["name"]
    send_chat_request_to_ui(
        from_User=current_bot_name, 
        to_User=other_bot_name, 
        message=response
    )
    cache_necessary_data(save=True, load=False)


def driver():
    global MODEL
    load_status = cache_necessary_data(load=True, save=False)
    print(f"Using {MODEL} as our agent model")
    if not load_status:
        inital_setup()
    conversation_loop()
    store_conversation_log()
    cache_necessary_data(save=True, load=False)


if __name__ == "__main__":
    driver()
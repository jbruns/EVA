#!/usr/bin/env python3

import re
import logging
import time
import queue
import threading
from typing import Callable

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from backends import BaseBackend, OllamaBackend
from lib.config import config

print(
    r"""
 ___________    ____  ___      
|   ____\   \  /   / /   \     
|  |__   \   \/   / /  ^  \    
|   __|   \      / /  /_\  \   
|  |____   \    / /  _____  \  
|_______|   \__/ /__/     \__\ 
                               
...with thanks to Fortyseven/ircawp

Starting up...
""".rstrip()
)

logging.basicConfig(level=config['log_level'])
logging.info(f"Log level = {config['log_level']}")

THREAD_SLEEP = config['thread_sleep']
logging.info(f"Thread sleep = {config['thread_sleep']}")

logging.info(f"OLLaMa endpoint = {config['ollama_api_endpoint']}")

# globals

logging.debug('Initializing slack queue.')
slack_queue: queue.Queue = queue.Queue()

backend_instance: BaseBackend | None = None

logging.debug('Initializing slack-bolt.')
bolt = App(token=config['SLACK_BOT_TOKEN'])

@bolt.event("app_mention")
def ingest_event(event, message, client, say, body):
    user_id = event["user"]
    channel = event["channel"]

    regex = r"(<.*> )(.*)"

    prompt = re.match(regex, event["text"], re.MULTILINE)[2]

    logging.debug(f"ingest_event: user_id = {user_id}, channel = {channel}, prompt = {prompt}, say = {say} // adding to queue.")
    add_to_queue(user_id, channel, prompt, say)

def add_to_queue(user_id: str, channel: str, message: str, say: Callable):
    """
    Add a message to the queue to be sent to Slack.

    Args:
        user_id (str): The user ID of the user who sent the message.
        channel (str): The channel ID of the channel the message was sent in.
        message (_type_): _description_
        say (_type_): _description_
    """
    logging.debug("add_to_queue")
    slack_queue.put((user_id, channel, message, say))

def process_queue_entry(user_id, channel, prompt, say):
    logging.info("==========================")
    logging.info(
        f"Processing queue entry for {user_id} with prompt '{prompt}'"
    )

    print("\n\n>>> Prompt: ", prompt)

    username = bolt.client.users_info(user=user_id)["user"]["profile"]["display_name"]

    response = backend_instance.query(prompt, username=username)

    logging.info(f"<<< Response: '{response}'")

    say(f"<@{user_id}>: {response}")

def process_queue():
    """
    Process the queue of messages to be sent to Slack until
    the heat death of the universe. But pause for a bit
    now and then.
    """
    logging.info("Starting queue processing thread...")

    while True:
        time.sleep(THREAD_SLEEP)
        if not slack_queue.empty():
            process_queue_entry(*slack_queue.get())


if __name__ == "__main__":
    backend_instance = OllamaBackend()

    queue_thread = threading.Thread(target=process_queue, daemon=True)
    queue_thread.start()

    SocketModeHandler(bolt, config['SLACK_APP_TOKEN']).start()

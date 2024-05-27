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
logging.info(f"[config] log_level = {config['log_level']}")

THREAD_SLEEP = config['thread_sleep']
logging.info(f"[config] thread_sleep = {config['thread_sleep']}")

# globals

slack_queue: queue.Queue = queue.Queue()
backend_instance: BaseBackend | None = None
bolt = App(token=config['SLACK_BOT_TOKEN'])
threads = {}

@bolt.event("app_mention")
def handle_mention(event, client, say):
    # https://api.slack.com/events/app_mention
    slack_queue.put((event, client, say))

@bolt.event("message")
def handle_message(event, client, say):
    # https://api.slack.com/events/message
    thread_ts = event.get("thread_ts", None) or event["ts"]
    if isKnownThread(thread_ts):
        slack_queue.put((event, client, say))

def processQueueItem(event, client, say):
    user_id = event["user"]
    channel = event["channel"]
    timestamp = event["ts"]
    thread_ts = event.get("thread_ts", None) or event["ts"]

    regex = r"(<.*> )(.*)"
    if re.match(regex, event['text'], re.MULTILINE) is not None:
        prompt = re.match(regex, event['text'], re.MULTILINE)[2]
    else:
        prompt = event['text']


    logging.debug(f"[processQueueItem]: user_id = {user_id}, channel = {channel}, thread_ts = {thread_ts}, prompt = {prompt}")

    # get the user's display name from Slack
    user_display_name = client.users_info(user=user_id)["user"]["profile"]["display_name"]
    # visual indication that we're working on it
    client.reactions_add(channel=channel,timestamp=timestamp,name="eyes")

    # is this a conversation that the bot is already participating in?
    if isKnownThread(thread_ts):
        logging.debug(f"[processQueueItem]: using existing thread context ({thread_ts})")
    else:
        # set initial context
        logging.debug(f"[processQueueItem]: new thread context ({thread_ts})")
        threads[thread_ts] = {}
        threads[thread_ts]['model'] = config['model']
        threads[thread_ts]['system'] = config['system_prompt']
        threads[thread_ts]['messages'] = []
    
    # add the latest user message
    threads[thread_ts]['messages'].append({'role': 'user', 'content': prompt})
    # bundle the objects to pass to the LLM
    model = threads[thread_ts]['model']
    system_prompt = threads[thread_ts]['system'].format(username=user_display_name)
    messages = threads[thread_ts]['messages']

    logging.debug(f"[processQueueItem]: sending to LLM. {thread_ts}|{model}|{system_prompt}|{messages}")
    response = backend_instance.query(model,system_prompt,messages)

    # add the response from the LLM to the thread context
    threads[thread_ts]['messages'].append({'role': 'assistant', 'content': response})

    # replace the waiting indicator with the response
    client.reactions_remove(channel=channel,timestamp=timestamp,name="eyes")
    say(response,thread_ts=thread_ts)

def isKnownThread(thread_ts):
    if thread_ts in threads.keys():
        return True
    else:
        return False
    
def process_queue():
    while True:
        time.sleep(THREAD_SLEEP)
        if not slack_queue.empty():
            processQueueItem(*slack_queue.get())

if __name__ == "__main__":
    logging.debug("[startup] initializing LLM backend.")
    backend_instance = OllamaBackend()

    logging.debug("[startup] initializing work queue.")
    queue_thread = threading.Thread(target=process_queue, daemon=True)
    queue_thread.start()

    logging.debug('[startup] initializing slack SocketModeHandler.')
    SocketModeHandler(bolt, config['SLACK_APP_TOKEN']).start()

    logging.info["[startup] ready. Listening for events."]

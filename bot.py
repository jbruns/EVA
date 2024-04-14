#!/usr/bin/env python3
import re
import logging
import time
import dotenv
import queue
import threading
from typing import Callable
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from backends import BaseBackend, LlamaCppBackend, OllamaBackend


from imagegen.BaseImageGen import BaseImageGen
from imagegen.SDXS import SDXS
from lib.config import config
from backends import BaseBackend

print(
    r"""
 __
|__|_______   ____  _____  __  _  ________
|  |\_  __ \_/ ___\ \__  \ \ \/ \/ /\____ \
|  | |  | \/\  \___  / __ \_\     / |  |_) )
|__| |__|    \___  )(____  / \/\_/  |   __/
                 \/      \/         |__|
-=-=-=-=-=-=-=-=-= BOOTING =-=-=-=-=-=-=-=-
""".rstrip()
)

# config
slack_creds = dotenv.dotenv_values(".env")
if not slack_creds["SLACK_APP_TOKEN"] or not slack_creds["SLACK_BOT_TOKEN"]:
    raise Exception("Slack credentials incomplete. Check .env file.")

THREAD_SLEEP = config.get("thread_sleep", 0.250)
logging.basicConfig(level=config.get("log_level", "INFO"))

# globals

slack_queue: queue.Queue = queue.Queue()

backend_instance: BaseBackend | None = None
imagegen_instance: BaseImageGen | None = None

bolt = App(token=slack_creds["SLACK_BOT_TOKEN"])


@bolt.event("app_mention")
def ingest_event(event, message, client, say, body):
    user_id = event["user"]
    regex = r"(<.*> )(.*)"

    prompt = re.match(regex, event["text"], re.MULTILINE)[2]

    add_to_queue(user_id, prompt, say)


def add_to_queue(user_id: str, message: str, say: Callable):
    """
    Add a message to the queue to be sent to Slack.

    Args:
        user_id (str): The user ID of the user who sent the message.
        message (_type_): _description_
        say (_type_): _description_
    """
    slack_queue.put((user_id, message, say))


def process_queue_entry(user_id, prompt, say):
    logging.info("==========================")
    logging.info(
        f"Processing queue entry for {user_id} with prompt '{prompt}'"
    )

    username = bolt.client.users_info(user=user_id)["user"]["profile"][
        "display_name"
    ]

    response, media = backend_instance.query(
        user_prompt=prompt, username=username
    )

    if media:
        print("Media detected. Uploading image...")
        pass

    logging.info(f"Response: '{response}'")

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
    match config.get("backend", "llamacpp"):
        case "llamacpp":
            backend_instance = LlamaCppBackend()
        case "ollama":
            backend_instance = OllamaBackend()

    imagegen = SDXS()

    queue_thread = threading.Thread(target=process_queue, daemon=True)
    queue_thread.start()

    SocketModeHandler(bolt, slack_creds["SLACK_APP_TOKEN"]).start()

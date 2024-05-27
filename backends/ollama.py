import logging
from datetime import datetime
from typing import Optional

from ollama import Client

from lib.config import config
from backends.BaseBackend import BaseBackend
from plugins import PLUGINS

LLM_MAX_TOKENS = 2048

class OllamaBackend(BaseBackend):
    ##################
    def __init__(self) -> None:
        self.model = config['model']
        self.api_endpoint = config['OLLAMA_API_ENDPOINT']
        self.client = Client(host=self.api_endpoint)

        logging.info(f"[OllamaBackend]: default model = {self.model}")
        logging.info(f"[OllamaBackend]: ollama_api_endpoint = {config['OLLAMA_API_ENDPOINT']}")

    ##################
    def process_plugin(self, cmd_query: str) -> tuple[str, str]:
        cmd_key = cmd_query.split(" ")[0].strip()[1:]

        for func in PLUGINS:
            if (
                hasattr(PLUGINS[func], "triggers")
                and cmd_key in PLUGINS[func].triggers
            ):
                cmd_plug = PLUGINS[func]

                query = ""

                if len(cmd_query.split()) > 1:
                    query = cmd_query[cmd_query.find(" ") :].strip()

                # strips everything before the first space
                return cmd_plug.execute(
                    query=query,
                    backend=self,
                )

        return "Unknown command. Try `/help`.", ""

    ##################
    def query(self, model, system_prompt, messages):
        try:
            self.start_time = datetime.now()

            self.options = {
                "temperature": config['temperature']
            }

            messages.insert(0, {'role': 'system', 'content': system_prompt})

            logging.debug(f"[OllamaBackend.query]: sending to ollama. {model}|{messages}|{self.options}")
            response = self.client.chat(
                model=model,
                messages=messages,
                options=self.options,
                keep_alive=0,
            )

            self.end_time = datetime.now()

            self.last_query_time = self.end_time - self.start_time

            response = response["message"]["content"].strip()

            # compress multiple newlines down to one
            response = "\n".join(
                [line for line in response.split("\n") if line.strip() != ""]
            )

            if len(response) == 0:
                response = "Response was empty. :("

        except RuntimeError as e:
            response = f"**IT HERTZ, IT HERTZ:** '{str(e)}'"

        return response

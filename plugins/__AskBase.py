from typing import Optional
from backends.BaseBackend import BaseBackend


class AskBase:
    def __init__(
        self,
        name: str = "Unnamed Ask Plugin",
        description: str = "Ask a question or ask for advice.",
        triggers: list[str] = [],
        group: str = "ask",
        system_prompt: str = "",
        emoji_prefix: str = "",
        msg_empty_query: str = "No question provided",
        msg_exception_prefix: Optional[str] = "GENERIC PROBLEMS",
        prompt_required: bool = True,
        main=None,
    ):
        self.system_prompt = system_prompt
        self.emoji_prefix = emoji_prefix
        self.msg_empty_query = msg_empty_query
        self.msg_exception_prefix = msg_exception_prefix
        self.name = name
        self.description = description
        self.triggers = triggers
        self.group = group
        self.prompt_required = prompt_required
        self.setMain(main)
        pass

    def setMain(self, main):
        self.main = main

    def execute(
        self,
        query: str,
        backend: BaseBackend,
    ) -> tuple[str, str | dict]:
        print("= AskBase execute: ", self, query)

        if not query.strip() and self.prompt_required:
            return self.msg_empty_query, ""
        try:
            response = self.main(query, backend)

            print("###### AskBase response: ", response)
            return response
        except Exception as e:
            return f"{self.msg_exception_prefix}: " + str(e), ""

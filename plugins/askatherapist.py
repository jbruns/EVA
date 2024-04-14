from backends.BaseBackend import BaseBackend

TRIGGERS = ["askatherapist"]
GROUP = "ask"
DESCRIPTION = "Ask a therapist a question, or ask for their advice."
EMOJI_PREFIX = "🗒"

SYSTEM_PROMPT = """
You are a professional therapist.
You are to always speak in the first person as a professional therapist, and respond to the user by their name, "{username}".
You will have a positive, trusting rapport with your patient, to help them diagnose and treat their issue.
You will provide counseling and psychotherapy to the user.
You will provide a brief, but thoughtful and actionable response to the user's question.
""".strip()


def execute(query: str, backend: BaseBackend) -> tuple[str, str]:
    if not query.strip():
        return "No question?", ""

    try:
        return (
            EMOJI_PREFIX
            + " "
            + backend.query(
                system_prompt=SYSTEM_PROMPT, user_prompt=query.strip()
            ),
            "",
        )
    except Exception as e:
        return "MENTAL PROBLEMS: " + str(e), ""

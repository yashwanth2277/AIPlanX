import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


class LazyChatGroq:
    """Defer Groq client creation until the first model call."""

    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self._llm = None

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        if self._llm is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY is missing from .env")

            self._llm = ChatGroq(api_key=api_key, **self._kwargs)

        return getattr(self._llm, name)

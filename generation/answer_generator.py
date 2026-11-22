import os
import re
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

from generation.prompt_builder import PromptMessages

load_dotenv()

MODEL = "gpt-4o-mini"
CITATION_RE = re.compile(r"\[Source: .+?, Section: .+?\]")


@dataclass
class Answer:
    text: str
    citations: List[str]
    query: str
    chunks_used: int


def generate(prompt: PromptMessages, query: str, chunks_used: int) -> Answer:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": prompt.user},
        ],
    )
    text = response.choices[0].message.content or ""
    return Answer(text=text, citations=CITATION_RE.findall(text), query=query, chunks_used=chunks_used)

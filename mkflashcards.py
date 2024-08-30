from openai import OpenAI
from pydantic import BaseModel, Field
from langchain_text_splitters import RecursiveCharacterTextSplitter
from textwrap import dedent
import json
import requests
import math

def llm(openai_api_key: str,
        model: str,
        response_model: BaseModel = BaseModel,
        system: str = None, user: str = None,
        **kwargs):
    oai = OpenAI(api_key=openai_api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    if user:
        messages.append({"role": "user", "content": user})
    result = oai.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=response_model,
        **kwargs,
    )
    return result.choices[0].message.parsed

class TextSummary(BaseModel):
    title: str = Field(..., description="Title (includes original title and author if available).")
    short_summary: str = Field(..., description="Short summary (1-2 sentences) of the text.")
    bullet_points: list[str] = Field(..., description="Summary of the text in up to 23 bullet points.")

def summarize_text(openai_api_key, model, txt):
    return llm(
        openai_api_key,
        model,
        TextSummary,
        'Read the user-provided text and summarize it in up to 23 bullet points.',
        txt
    )

def get_chunks(txt):
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name='gpt-4o',
        chunk_size=5000,
        chunk_overlap=50,
    )
    return text_splitter.split_text(txt)

class Flashcard(BaseModel):
    front: str = Field(..., description=(
        'Front of the flashcard (question or prompt for remembering the topic of the card). '
        'Single sentence, formatted as Markdown.'
    ))
    back: str = Field(..., description=(
        'Back of the flashcard (answer or information to remember). '
        'Short paragrah. Include lists or other formatting to make the '
        'information easier to remember. Formatted as Markdown.'
    ))
    quote: str = Field(..., description=(
        'Quote from the text that the flashcard is based on. '
        'Include a short verbarim excerpt from the text that the flashcard is based on.'
    ))

class FlashcardSet(BaseModel):
    flashcards: list[Flashcard]

def get_flashcards(openai_api_key, model, txt, num_flashcards, tags):
    flashcard_infos = []
    context = summarize_text(openai_api_key, model, txt).dict()
    chunks = get_chunks(txt)
    flashcards_per_chunk = round(num_flashcards / len(chunks))

    for chunk in chunks:
        system = dedent(f"""
        You are an expert tutor and flashcards creator.
        You help the user remember the most important
        information from the text by creating flashcards.
        The text in the flashcards should be concise and authoritative.
        Don't use phrases like "according to the author" or "in the artice",
        just present the information as if it were a fact.
        The user-provided input includes `context`, with information about the document
        and a summary of the entire document in bullet points, and `chunk`,
        a part of the text to focus on when creating the flashcards.
        Read the user-provided input carefully and generate
        {flashcards_per_chunk} flashcards. IMPORTANT: IT IS CRUCIAL
        THAT YOU GENERATE EXACTLY {flashcards_per_chunk} FLASHCARDS.
        """).strip()

        user_input = { 'context': context, 'chunk': chunk }

        flashcard_infos += llm(
            openai_api_key,
            model,
            FlashcardSet,
            system,
            json.dumps(user_input),
        ).flashcards

    flashcards = []
    for flashcard_info in flashcard_infos:
        flashcard_md = f'### {flashcard_info.front.strip()}\n---\n{flashcard_info.back.strip()}\n\n> {flashcard_info.quote.strip()}'
        if tags is not None:
            flashcard_md += f"\n\n{' '.join(['#' + tag for tag in tags])}"
        flashcards.append(flashcard_md.strip())
    
    return flashcards

def fetch_text(url, jina_api_key):
    return requests.get(
        f'https://r.jina.ai/{url}',
        headers={'Authorization': f'Bearer {jina_api_key}'}
    ).text

def generate_flashcards(openai_api_key, model, text, num_flashcards, tags_str=''):
    tags = None if tags_str.strip() == '' else [tag.strip() for tag in tags_str.split(' ')]
    flashcards = get_flashcards(openai_api_key, model, text, num_flashcards, tags)
    return '\n===\n'.join(flashcards)

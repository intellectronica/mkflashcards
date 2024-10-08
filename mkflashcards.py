from pydantic import BaseModel, Field
from langchain_text_splitters import RecursiveCharacterTextSplitter
import instructor
from textwrap import dedent
import json
import requests
import math
import random
from functools import partial
import asyncio
import itertools
import os

def get_llm_api_func(model, api_key):
    if model.startswith('gpt'):
        from openai import AsyncOpenAI
        aoai = AsyncOpenAI(api_key=api_key)
        if os.getenv('LOGFIRE_TOKEN') is not None:
            import logfire
            logfire.instrument_openai(aoai)
        return partial(instructor.from_openai(
            client=aoai,
            mode=instructor.Mode.TOOLS_STRICT,
        ).chat.completions.create, model=model)
    elif model.startswith('gemini'):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return instructor.from_gemini(
            client=genai.GenerativeModel(model),
            mode=instructor.Mode.GEMINI_JSON,
            use_async=True,
        ).messages.create
    else:
        raise ValueError(f'Unknown model: {model}')

def llm(api_key: str,
        model: str,
        response_model: BaseModel = BaseModel,
        system: str = None, user: str = None,
        **kwargs):
    ai_func = get_llm_api_func(model, api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    if user:
        messages.append({"role": "user", "content": user})
    return ai_func(
        response_model=response_model,
        messages=messages,
        **kwargs,
    )

def fit_text(txt, max_length=345678, chunk_size=1234):
    if len(txt) <= max_length:
        return txt
    chunks = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name='gpt-4o',
        chunk_size=1234,
        chunk_overlap=0,
    ).split_text(txt)
    num_chunks_to_remove = math.ceil(len(chunks) * ((len(txt) - max_length)) / len(txt))
    chunk_idxs_to_remove = random.sample(range(1, len(chunks) - 1), num_chunks_to_remove)
    remaining_chunks = [chunk for idx, chunk in enumerate(chunks) if idx not in chunk_idxs_to_remove]
    short_text = '\n\n...\n\n'.join(remaining_chunks)
    return short_text

class TextSummary(BaseModel):
    title: str = Field(..., description="Title (includes original title and author if available).")
    short_summary: str = Field(..., description="Short summary (1-2 sentences) of the text.")
    bullet_points: list[str] = Field(..., description="Summary of the text in up to 23 bullet points.")

async def summarize_text(api_key, model, txt):
    max_length = 678987 if model.startswith('gemini') else 345678
    return await llm(
        api_key,
        model,
        TextSummary,
        'Read the user-provided text and summarize it with a title, short summary, and up to 23 bullet points.',
        fit_text(txt, max_length=max_length),
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
        'Include a short (2-3 sentences) verbarim excerpt from the text that the flashcard is based on.'
    ))

class FlashcardSet(BaseModel):
    flashcards: list[Flashcard]

async def get_chunk_flashcards(api_key, model, context, chunk, system):
    user_input = { 'context': context, 'chunk': chunk }
    return (await llm(
        api_key,
        model,
        FlashcardSet,
        system,
        json.dumps(user_input),
    )).flashcards

async def get_flashcards(api_key, model, txt, num_flashcards):
    context = (await summarize_text(api_key, model, txt)).dict()
    chunks = get_chunks(txt)
    flashcards_per_chunk = math.ceil(num_flashcards / len(chunks))

    system = dedent(f"""
    You are an expert tutor and flashcards creator.
    You help the user remember the most important
    information from the text by creating flashcards.
    The text in the flashcards should be concise and authoritative.
    Don't use phrases like "according to the author" or "in the artice"
    or "according to the text", just present the information as if it were a fact.
    The user-provided input includes `context`, with information about the document
    and a summary of the entire document in bullet points, and `chunk`,
    a part of the text to focus on when creating the flashcards.
    Read the user-provided input carefully and generate
    {flashcards_per_chunk} flashcards.
    IMPORTANT: IT IS CRUCIAL THAT YOU FOLLOW THE INSTRUCTIONS ABOVE EXACTLY.
    """).strip()

    tasks = [get_chunk_flashcards(api_key, model, context, chunk, system) for chunk in chunks]
    results = await asyncio.gather(*tasks)
    flashcard_infos = list(itertools.chain(*results))

    return flashcard_infos

def fetch_text(url, jina_api_key):
    return requests.get(
        f'https://r.jina.ai/{url}',
        headers={'Authorization': f'Bearer {jina_api_key}'}
    ).text


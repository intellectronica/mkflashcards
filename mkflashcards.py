from pydantic import BaseModel, Field
from langchain_text_splitters import RecursiveCharacterTextSplitter
import instructor
from bs4 import BeautifulSoup
from textwrap import dedent
import json
import requests
import math
import random
from functools import partial
import asyncio
import itertools
import os

OPENAI_MODEL = 'gpt-4o-2024-11-20'

def get_llm_api_func(model, api_key):
    from openai import AsyncOpenAI
    aoai = AsyncOpenAI(api_key=api_key)
    if os.getenv('LOGFIRE_TOKEN') is not None:
        import logfire
        logfire.instrument_openai(aoai)
    return partial(instructor.from_openai(
        client=aoai,
        mode=instructor.Mode.TOOLS_STRICT,
    ).chat.completions.create, model=model)

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
        chunk_size=345,
        chunk_overlap=0,
    ).split_text(txt)
    num_chunks_to_remove = math.ceil(len(chunks) * ((len(txt) - max_length)) / len(txt))
    chunk_idxs_to_remove = random.sample(range(1, len(chunks) - 1), num_chunks_to_remove)
    remaining_chunks = [chunk for idx, chunk in enumerate(chunks) if idx not in chunk_idxs_to_remove]
    short_text = '\n\n...\n\n'.join(remaining_chunks)
    return short_text

class TextSummary(BaseModel):
    title: str = Field(..., description="Title (includes original title and author if available).")
    summary: str = Field(..., description="One-pager summary of the text (roughly 500 tokens).")

async def summarize_text(api_key, txt):
    max_length = 345678
    result = await llm(
        api_key,
        OPENAI_MODEL,
        TextSummary,
        'Read the user-provided text and summarize it with a title and a one-pager summary.',
        fit_text(txt, max_length=max_length),
    )
    summary = dedent(f"""
    <context>
      <title>{result.title}</title>
      <summary>
        {result.summary}
      </summary>
    </context>        
    """).strip()
    return summary

def get_chunks(txt):
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name='gpt-4o',
        chunk_size=3333,
        chunk_overlap=333,
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
        'Quote from the chunk that the flashcard is based on. '
        'Include a short (2-3 sentences) verbarim excerpt from the chunk that the flashcard is based on.'
    ))

class FlashcardSet(BaseModel):
    flashcards: list[Flashcard]

async def get_chunk_flashcards(api_key, summary, chunk, system):
    prompt = f'{summary}\n<chunk>\n{chunk}\n</chunk>\n\n{system}'
    return (await llm(
        api_key,
        OPENAI_MODEL,
        FlashcardSet,
        user=prompt,
    )).flashcards

async def get_flashcards(api_key, txt, num_flashcards):
    summary = await summarize_text(api_key, txt)
    chunks = get_chunks(txt)
    flashcards_per_chunk = math.ceil(num_flashcards / len(chunks))

    system = dedent(f"""
    You are an expert tutor and flashcards creator. \
    You help the user remember the most important \
    information from the text by creating flashcards.

    The text in the flashcards should be concise and authoritative. \
    Don't use phrases like "according to the author" or "in the artice" \
    or "according to the text", just present the information as if it were a fact.
    GOOD EXAMPLE: "What is the best way to peel a poptato?"
    BAD EXAMPLES:
        "According to the article, what is the best way to peel a potato?",
        "What is Jamie Oliver's favorite way to peel a potato?"
        "How does the author suggest peeling a potato?"
        "How does the book approach the question of potato peeling?"

    The user-provided input above includes <context>...</context>, with \
    information about the document and a summary of the entire document \
    in bullet points, and <chunk>...</chunk>, a part of the document text \
    to focus on when creating the flashcards.

    Start by reviewing the context. Then, read the chunk carefully and \
    generate EXACTLY {flashcards_per_chunk} FLASHCARDS based on the contents of \
    the chunk. You must not generate more or fewer flashcards than the \
    {flashcards_per_chunk} specified.
    
    ONLY USE THE CONTENTS OF THE CHUNK FOR THE FLASHCARDS AND QUOTES.
    NEVER RELY ON TEXT FROM THE SUMMARY FOR THE FOCUS OF THE FLASHCARDS \
    OR THE QUOTES.

    IMPORTANT: IT IS CRUCIAL THAT YOU FOLLOW THE INSTRUCTIONS ABOVE EXACTLY.
    """).strip()

    first_result = await get_chunk_flashcards(api_key, summary, chunks[0], system)
    tasks = [get_chunk_flashcards(api_key, summary, chunk, system) for chunk in chunks[1:]]
    other_results = await asyncio.gather(*tasks)
    results = [first_result] + other_results
    flashcard_infos = list(itertools.chain(*results))

    return flashcard_infos

def fix_html(input_html):
    soup = BeautifulSoup(input_html, 'html.parser')
    if not soup.html:
        html_tag = soup.new_tag('html')
        html_tag.contents = soup.contents
        soup = BeautifulSoup(str(html_tag), 'html.parser')
    if not soup.html:
        html_tag = soup.new_tag('html')
        html_tag.append(*soup.contents)
        soup.append(html_tag)
    if not soup.head:
        head_tag = soup.new_tag('head')
        soup.html.insert(0, head_tag)
    if not soup.body:
        body_tag = soup.new_tag('body')
        for element in list(soup.html.contents):
            if element != soup.head:
                body_tag.append(element.extract())
        soup.html.append(body_tag)
    for element in list(soup.contents):
        if element != soup.html:
            soup.html.body.append(element.extract())
    formatted_html = soup.prettify()
    return formatted_html

def fetch_text(jina_api_key, url=None, content=None, content_ext=None):
    if url:
        return requests.get(
            f'https://r.jina.ai/{url}',
            headers={'Authorization': f'Bearer {jina_api_key}'}
        ).text
    elif content:
        payload = { 'url': 'http://example.com/' }
        if content_ext == 'pdf':
            payload['pdf'] = content
        elif content_ext == 'html':
            payload['html'] = fix_html(content)
        else:
            raise ValueError(f'Unsupported content type: {content_ext}')
        return requests.post(
            f'https://r.jina.ai/',
            headers={
                'Authorization': f'Bearer {jina_api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
        ).text

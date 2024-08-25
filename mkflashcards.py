from openai import OpenAI
from pydantic import BaseModel, Field
import tiktoken
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
    print("LLM: ", system[:123], user[:123]) # DEBUG
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

def token_count(txt):
    enc = tiktoken.encoding_for_model('gpt-4o')
    return len(enc.encode(txt))

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
    print(f"Chunks: {len(chunks)} Flashcards per chunk: {flashcards_per_chunk}") # DEBUG

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
    print(f'Fetching text from {url}')
    return requests.get(
        f'https://r.jina.ai/{url}',
        headers={'Authorization': f'Bearer {jina_api_key}'}
    ).text

def generate_flashcards(openai_api_key, model, text, num_flashcards, tags_str=''):
    tags = None if tags_str.strip() == '' else [tag.strip() for tag in tags_str.split(' ')]
    flashcards = get_flashcards(openai_api_key, model, text, num_flashcards, tags)
    print(f"Generated {len(flashcards)} flashcards.") # DEBUG
    return '\n===\n'.join(flashcards)

def update_num_flashcards(text):
    num_tokens = token_count(text)
    return max(min(math.ceil(num_tokens / 123), 1000), 10), str(num_tokens)

ABOUT = """
# Make Flashcards, automagically, with AI!

This app uses AI to generate flashcards from a piece of text.

## Instructions
1. Enter your OpenAI API key. It will be used for generating the flashcards. You can get an API key from [OpenAI](https://platform.openai.com/). API keys are pased to the server for processing but not stored on the server (they are stored locally in your browser for you convenience - remove after use if necessary).
2. If you'd like to fetch text from a URL (web page, PDF, etc...), enter the URL and your Jina API key, then click "Fetch Text". You can get a Jina API key from [Jina](https://jina.ai/).
3. You can also just paste the text directly into the "Text" box.
4. The app will suggest a number of flashcards to generate based on the length of the text. You can adjust this number if you like.
5. Optionally, you can add tags to the flashcards. The format is a space-separated list of tags *(e.g. "biology philosophy science-fiction")*.
6. Click "Generate Flashcards" to generate the flashcards. Wait a bit.
7. The flashcards will appear in the "Flashcards" box. The format is Markdown, with the front and the back separated by `---` and cards separated by `===`. You can copy and import into your favourite spaced-repetition app.
  - (If you're using [Mochi](https://mochi.cards/), you can easily import the flashcars by saving the text to a `.md` file, and importing it using the Markdown format from a single file and entering `===` as the cards separator.)

---

- Created by [intellectronica](https://intellectronica.net/).
- Source code on at [github.com/intellectronica/mkflashcards](https://github.com/intellectronica/mkflashcards).

Enjoy!
"""
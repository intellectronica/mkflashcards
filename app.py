from openai import OpenAI
from pydantic import BaseModel, Field
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter
from textwrap import dedent
import json
import math

def llm(response_model: BaseModel = BaseModel,
        system: str = None, user: str = None,
        **kwargs):
    print("LLM: ", system[:123], user[:123]) # DEBUG
    oai = OpenAI()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    if user:
        messages.append({"role": "user", "content": user})
    result = oai.beta.chat.completions.parse(
        model='gpt-4o-2024-08-06',
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

def summarize_text(txt):
    return llm(
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

def get_flashcards(txt, num_flashcards, tags):
    flashcard_infos = []
    context = summarize_text(txt).dict()
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

import gradio as gr
import os

def generate_flashcards(text, num_flashcards, tags_str=''):
    tags = None if tags_str.strip() == '' else [tag.strip() for tag in tags_str.split(' ')]
    flashcards = get_flashcards(text, num_flashcards, tags)
    print(f"Generated {len(flashcards)} flashcards.") # DEBUG
    return '\n===\n'.join(flashcards)

def update_num_flashcards(text):
    num_tokens = token_count(text)
    return max(min(math.ceil(num_tokens / 123), 1000), 10), str(num_tokens)

def update_openai_api_key(openai_api_key):
    os.environ['OPENAI_API_KEY'] = openai_api_key

with gr.Blocks() as mkflashcards:
    openai_api_key = gr.Textbox(label="OPENAI_API_KEY", type='password', value=os.getenv('OPENAI_API_KEY', ''))
    text = gr.Textbox(label="Text", lines=7, max_lines=7)
    num_tokens = gr.Markdown('')
    with gr.Row():
        num_flashcards = gr.Number(value=23, minimum=10, maximum=1000, label="Number of flashcards to generate")
        tags = gr.Textbox(label="Tags")
        generate_btn = gr.Button("Generate Flashcards")
    output = gr.Textbox(label="Flashcards", lines=23, max_lines=123, autoscroll=False, interactive=True)
    generate_btn.click(fn=generate_flashcards, inputs=[text, num_flashcards, tags], outputs=output, api_name="generate-flashcards")
    text.change(fn=update_num_flashcards, inputs=text, outputs=[num_flashcards, num_tokens])
    openai_api_key.change(fn=update_openai_api_key, inputs=openai_api_key)

gr.close_all()
mkflashcards.launch()
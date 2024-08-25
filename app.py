import os

import fasthtml.common as fh
from markdown import markdown

from mkflashcards import *

def app_js():
    with open('app.js') as f:
        return f.read()

app, rt = fh.fast_app(
    hdrs=[fh.Script(app_js())],
)

@app.post('/-/fetch-text')
async def do_fetch_text(jina_api_key: str, url: str, *args, **kwargs):
    return fetch_text(url, jina_api_key)

@app.post('/-/generate-flashcards')
async def do_fetch_text(openai_api_key: str, model: str, num_flashcards: int, tags: str, text: str, *args, **kwargs):
    return generate_flashcards(openai_api_key, model, text, num_flashcards, tags)

@app.get("/")
def home():
    return fh.Form(
        fh.Container(
            fh.Card(fh.NotStr(markdown(ABOUT))),
            fh.Grid(
                fh.Group(
                    fh.B('OPENAI_API_KEY'),
                    fh.Input(name='openai_api_key', type='password', value=os.getenv('OPENAI_API_KEY', ''), id='openai_api_key'),
                ),
                fh.Group(
                    fh.B('Model'),
                    fh.Select(
                        fh.Option('gpt-4o-mini', selected=True),
                        fh.Option('gpt-4o-2024-08-06'),
                        name='model', id='model',
                    ),
                ),
            ),
            fh.Grid(
                fh.Group(
                    fh.B('JINA_API_KEY'),
                    fh.Input(name='jina_api_key', type='password', value=os.getenv('JINA_API_KEY', ''), id='jina_api_key'),
                ),
                fh.Group(
                    fh.B('URL'),
                    fh.Input(name='url', type='text', id='url'),
                ),
                fh.Button('Fetch Text', hx_post='/-/fetch-text', hx_target='#text', hx_swap='innerHTML'),
            ),
            fh.Group(
                fh.B('Text'),
                fh.Textarea(name='text', rows=7, id='text'),
            ),
            fh.Grid(
                fh.Group(
                    fh.B('Number of flashcards to generate'),
                    fh.Input(name='num_flashcards', type='number', value=23, id='num_flashcards'),
                ),
                fh.Group(
                    fh.B('Tags'),
                    fh.Input(name='tags', type='text', id='tags'),
                ),
                fh.Button('Generate Flashcards', hx_post='/-/generate-flashcards', hx_target='#flashcards', hx_swap='innerHTML'),
            ),
            fh.Group(
                fh.B('Flashcards'),
                fh.Textarea(rows=23, id='flashcards'),
            ),
        ),
    )

fh.serve()

import os

from fasthtml.common import *
from markdown import markdown

from mkflashcards import *

def app_js():
    with open('app.js') as f:
        return f.read()

app, rt = fast_app(
    hdrs=[Script(app_js())],
)

@app.post('/-/fetch-text')
async def do_fetch_text(jina_api_key: str, url: str, *args, **kwargs):
    return fetch_text(url, jina_api_key)

@app.post('/-/generate-flashcards')
async def do_fetch_text(openai_api_key: str, model: str, num_flashcards: int, tags: str, text: str, *args, **kwargs):
    return generate_flashcards(openai_api_key, model, text, num_flashcards, tags)

@app.get("/")
def home():
    return Form(
        Container(
            Card(NotStr(markdown(ABOUT))),
            Grid(
                Group(
                    B('OPENAI_API_KEY'),
                    Input(name='openai_api_key', type='password', value=os.getenv('OPENAI_API_KEY', ''), id='openai_api_key'),
                ),
                Group(
                    B('Model'),
                    Select(
                        Option('gpt-4o-mini', selected=True),
                        Option('gpt-4o-2024-08-06'),
                        name='model', id='model',
                    ),
                ),
            ),
            Grid(
                Group(
                    B('JINA_API_KEY'),
                    Input(name='jina_api_key', type='password', value=os.getenv('JINA_API_KEY', ''), id='jina_api_key'),
                ),
                Group(
                    B('URL'),
                    Input(name='url', type='text', id='url'),
                ),
                Button('Fetch Text', hx_post='/-/fetch-text', hx_target='#text', hx_swap='innerHTML'),
            ),
            Group(
                B('Text'),
                Textarea(name='text', rows=7, id='text'),
            ),
            Grid(
                Group(
                    B('Number of flashcards to generate'),
                    Input(name='num_flashcards', type='number', value=23, id='num_flashcards'),
                ),
                Group(
                    B('Tags'),
                    Input(name='tags', type='text', id='tags'),
                ),
                Button('Generate Flashcards', hx_post='/-/generate-flashcards', hx_target='#flashcards', hx_swap='innerHTML'),
            ),
            Group(
                B('Flashcards'),
                Textarea(rows=23, id='flashcards'),
            ),
        ),
    )

serve()

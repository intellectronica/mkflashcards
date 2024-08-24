import os

import fasthtml.common as fh
from markdown import markdown

from mkflashcards import *

app, rt = fh.fast_app(live=True)

@app.get("/")
def home():
    return (
        fh.Container(
            fh.Card(fh.NotStr(markdown(ABOUT))),
            fh.Group(
                fh.B('OPENAI_API_KEY'),
                fh.Input(type='password', value=os.getenv('OPENAI_API_KEY', ''), id='OPENAI_API_KEY'),
            ),
            fh.Grid(
                fh.Group(
                    fh.B('JINA_API_KEY'),
                    fh.Input(type='password', value=os.getenv('JINA_API_KEY', ''), id='JINA_API_KEY'),
                ),
                fh.Group(
                    fh.B('URL'),
                    fh.Input(type='text', id='URL'),
                ),
                fh.Button('Fetch Text'),
            ),
            fh.Group(
                fh.B('Text'),
                fh.Textarea(rows=7, id='TEXT'),
            ),
            fh.Grid(
                fh.Group(
                    fh.B('Number of flashcards to generate'),
                    fh.Input(type='number', value=23, id='NUM_FLASHCARDS'),
                ),
                fh.Group(
                    fh.B('Tags'),
                    fh.Input(type='text', id='TAGS'),
                ),
                fh.Button('Generate Flashcards'),
            ),
            fh.Group(
                fh.B('Flashcards'),
                fh.Textarea(rows=23, id='FLASHCARDS'),
            ),
        ),
    )

fh.serve()

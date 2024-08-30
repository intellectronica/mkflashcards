import os

from fasthtml.common import *
from markdown import markdown

from mkflashcards import *

app, rt = fast_app(
    hdrs=[Script(src='/app.js'), Style(src='/app.css')],
)

@app.post('/-/fetch-text')
async def do_fetch_text(jina_api_key: str, url: str, *args, **kwargs):
    return fetch_text(url, jina_api_key)

@app.post('/-/generate-flashcards')
async def do_generate_flashcards(openai_api_key: str, model: str, num_flashcards: int, tags: str, text: str, *args, **kwargs):
    tags_lst = None if tags.strip() == '' else [tag.strip() for tag in tags.split(' ')]
    flashcard_mds = []
    flashcards= get_flashcards(openai_api_key, model, text, num_flashcards)
    for flashcard in flashcards:
        flashcard_md = f'### {flashcard.front.strip()}\n---\n{flashcard.back.strip()}\n\n> {flashcard.quote.strip()}'
        if tags_lst is not None:
            flashcard_md += f"\n\n{' '.join(['#' + tag for tag in tags_lst])}"
        flashcard_mds.append(flashcard_md.strip())
    return '\n===\n'.join(flashcard_mds)

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

@app.get("/")
def home():
    return Title('MkFlashcards'), Form(
        Container(
            Card(NotStr(markdown(ABOUT))),
            Grid(
                Div(
                    B('OPENAI_API_KEY'),
                    Input(name='openai_api_key', type='password', value=os.getenv('OPENAI_API_KEY', ''), id='openai_api_key'),
                ),
                Div(
                    B('Model'),
                    Select(
                        Option('gpt-4o-mini', selected=True),
                        Option('gpt-4o-2024-08-06'),
                        name='model', id='model',
                    ),
                ),
            ),
            Grid(
                Div(
                    B('JINA_API_KEY'),
                    Input(name='jina_api_key', type='password', value=os.getenv('JINA_API_KEY', ''), id='jina_api_key'),
                ),
                Div(
                    B('URL'),
                    Input(name='url', type='text', id='url'),
                ),
                Div(
                    Img(src='/spinner.svg', cls='htmx-indicator', id='fetch_spinner'),
                    Button('Fetch Text', hx_post='/-/fetch-text', hx_target='#text', hx_swap='innerHTML', hx_indicator='#fetch_spinner'),
                )
            ),
            Div(
                B('Text'),
                Textarea(name='text', rows=7, id='text', style='font-family: monospace'),
            ),
            Grid(
                Div(
                    B('Number of flashcards to generate'),
                    Input(name='num_flashcards', type='number', value=23, id='num_flashcards'),
                ),
                Div(
                    B('Tags'),
                    Input(name='tags', type='text', id='tags'),
                ),
                Div(
                    Img(src='/spinner.svg', cls='htmx-indicator', id='generate_spinner'),
                    Button('Generate Flashcards', hx_post='/-/generate-flashcards', hx_target='#flashcards', hx_swap='innerHTML', hx_indicator='#generate_spinner'),
                ),
            ),
            Div(
                B('Flashcards'),
                Textarea(name='flashcards', rows=13, id='flashcards', style='font-family: monospace'),
                Button('Download', id='download'),
            ),
        ),
    )

serve()
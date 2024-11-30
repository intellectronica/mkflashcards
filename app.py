import os
import tempfile
import asyncio
import base64
import subprocess
import tempfile

from fasthtml.common import *
from markdown import markdown
import hashlib

from mkflashcards import *

app, rt = fast_app(
    hdrs=[Script(src='/app.js'), Style(src='/app.css')],
)

if os.getenv('LOGFIRE_TOKEN') is not None:
    import logfire
    logfire.configure()
    logfire.instrument_requests()
    logfire.instrument_starlette(app)

def epub_to_html(epub_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as epub_file:
        epub_file_path = epub_file.name
        epub_file.write(epub_bytes)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as html_file:
        html_file_path = html_file.name

    try:
        subprocess.run(
            ['pandoc', epub_file_path, '-t', 'html', '-o', html_file_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
            
    except subprocess.CalledProcessError as e:
        print(f"Pandoc conversion failed: {e.stderr.decode('utf-8')}")
        html_content = ""
        
    finally:
        os.remove(epub_file_path)
        os.remove(html_file_path)
        
    return html_content

@app.post('/-/fetch-text')
async def do_fetch_text(request, jina_api_key: str, url: str, content: UploadFile = None):
    content_data, content_text, content_ext = None, None, None
    if content is not None and content.filename is not None:
        content_data = await content.read()
        content_ext = os.path.splitext(content.filename)[1].replace('.', '')    
        if content_ext == 'pdf':
            content_text = base64.b64encode(content_data).decode('utf-8')
        elif content_ext == 'html':
            content_text = content_data.decode('utf-8')
        elif content_ext == 'epub':
            content_text = epub_to_html(content_data)
            content_ext = 'html'
        else:
            raise ValueError(f'Unsupported file type: {content_ext}')
    return fetch_text(
        jina_api_key,
        url=(len(url.strip()) > 0 and url or None),
        content=content_text,
        content_ext=content_ext,
    )

def md_quote(txt):
    return '\n'.join([f'> {line}' for line in txt.splitlines()])

def get_task_tempfile_path(task_id):
    return os.path.join(tempfile.gettempdir(), f'{task_id}.md')

async def generate_flashcards_task(api_key, text, num_flashcards, task_id):
    flashcards = await get_flashcards(api_key, text, num_flashcards)
    flashcard_mds = []
    for flashcard in flashcards:
        flashcard_md = f'### {flashcard.front.strip()}\n---\n{flashcard.back.strip()}\n\n{md_quote(flashcard.quote.strip())}'
        flashcard_mds.append(flashcard_md.strip())
    flashcards_md = '\n===\n'.join(flashcard_mds)
    with open(get_task_tempfile_path(task_id), 'w') as file:
        file.write(flashcards_md)

@app.post('/-/generate-flashcards/{task_id}')
async def do_generate_flashcards(num_flashcards: int, text: str, task_id: str = '', request = None):
    if task_id == '':
        task_id = hashlib.md5(text.encode()).hexdigest()
        form = await request.form()
        api_key = form['openai_api_key']
        asyncio.create_task(generate_flashcards_task(api_key, text, num_flashcards, task_id))

    flashcards_md = None
    if os.path.exists(get_task_tempfile_path(task_id)):
        with open(get_task_tempfile_path(task_id), 'r') as file:
            flashcards_md = file.read()
        os.remove(get_task_tempfile_path(task_id))
    if flashcards_md is None:
        return Textarea(
            f'Generating flashcards ({task_id})...',
            name='flashcards', rows=13, id='flashcards', style='font-family: monospace',
            hx_post=f'/-/generate-flashcards/{task_id}',
            hx_trigger='every 1s', hx_swap='outerHTML',
        )
    else:
        return Textarea(flashcards_md, name='flashcards', rows=13, id='flashcards', style='font-family: monospace'),

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

def PersistentInput(**kwargs):
    kwargs['hx_on_input'] = 'persistentInputOnInput(this)'
    return (
        Input(**kwargs),
        Script(f"""
        persistentInputOnLoad('{kwargs["id"]}');
        """),
    )

@app.get("/")
def home():
    return Title('MkFlashcards'), Form(
        Container(
            # Card(NotStr(markdown(ABOUT))),
            Grid(
                Div(
                    B('OPENAI_API_KEY'),
                    PersistentInput(name='openai_api_key', type='password', value=os.getenv('OPENAI_API_KEY', ''), id='openai_api_key'),
                ),
            ),
            Grid(
                Div(
                    B('JINA_API_KEY'),
                    PersistentInput(name='jina_api_key', type='password', value=os.getenv('JINA_API_KEY', ''), id='jina_api_key'),
                ),
                Div(
                    B('URL'),
                    Input(name='url', type='text', id='url'),
                ),
                Div(
                    B('File (html/pdf/epub)'),
                    Input(name='content', type='file', multiple=False, required=False, id='content'),
                ),
                Div(
                    Img(src='/spinner.svg', cls='htmx-indicator', id='fetch_spinner'),
                    Button('Fetch Text', hx_post='/-/fetch-text', hx_target='#text', hx_swap='innerHTML', hx_indicator='#fetch_spinner'),
                )
            ),
            Div(
                B('Text'),
                Textarea(name='text', rows=7, id='text', style='font-family: monospace', hx_on_change='textOnChange()', hx_on__after_swap='textOnChange()'),
            ),
            Grid(
                Div(
                    B('Number of flashcards to generate'),
                    Input(name='num_flashcards', type='number', value=23, id='num_flashcards'),
                ),
                Div(
                    Img(src='/spinner.svg', cls='htmx-indicator', id='generate_spinner'),
                    Button('Generate Flashcards', hx_post='/-/generate-flashcards/', hx_target='#flashcards', hx_swap='outerHTML', hx_indicator='#generate_spinner'),
                ),
            ),
            Div(
                B('Flashcards'),
                Textarea(name='flashcards', rows=13, id='flashcards', style='font-family: monospace'),
                Button('Download', id='download', hx_on_click='downloadOnClick(event)'),
            ),
        ),
        hx_encoding='multipart/form-data',
    )

serve()
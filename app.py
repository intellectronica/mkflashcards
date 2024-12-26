"""MkFlashcards app: FastHTML UI and backend processes."""

import asyncio
import base64
import hashlib
import os
import subprocess
import tempfile

from fasthtml.common import A, Div, Form, Img, Link, P, Script, Title, UploadFile, fast_app, serve

from bulma import (
    Button,
    Card,
    CardContent,
    CardHeader,
    CardHeaderTitle,
    Column,
    Columns,
    Container,
    Input,
    Label,
    Textarea,
)
from mkflashcards import fetch_text, get_flashcards

app, _ = fast_app(
    pico=False,
    hdrs=[
        Link(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css",
            type="text/css",
        ),
        Link(
            rel="stylesheet",
            href="/app.css",
            type="text/css",
        ),
        Script(src='/app.js'),
    ],
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
            stderr=subprocess.PIPE,
        )

        with open(html_file_path, encoding='utf-8') as file:
            html_content = file.read()

    except subprocess.CalledProcessError:
        html_content = ""

    finally:
        os.remove(epub_file_path)
        os.remove(html_file_path)

    return html_content

@app.post('/-/fetch-text')
async def do_fetch_text(jina_api_key: str, url: str, content: UploadFile = None):
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
        url=((len(url.strip()) > 0 and url) or None),
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
        flashcard_md = (
            f'### {flashcard.front.strip()}\n---\n'
            f'{flashcard.back.strip()}\n\n'
            f'{md_quote(flashcard.quote.strip())}'
        )
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
        with open(get_task_tempfile_path(task_id)) as file:
            flashcards_md = file.read()
        os.remove(get_task_tempfile_path(task_id))
    if flashcards_md is None:
        return Textarea(
            f'Generating flashcards ({task_id})...',
            name='flashcards', rows=13, id='flashcards', style='font-family: monospace',
            hx_post=f'/-/generate-flashcards/{task_id}',
            hx_trigger='every 1s', hx_swap='outerHTML',
        )
    return Textarea(
        flashcards_md,
        name='flashcards',
        rows=13,
        id='flashcards',
        style='font-family: monospace',
    )

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
            Card(
                CardHeader(
                    CardHeaderTitle('MkFlashcards'),
                ),
                CardContent(
                    P('Make Flashcards, automagically, with AI!'),
                    P(
                        A('github.com/intellectronica/mkflashcards',
                          href='https://github.com/intellectronica/mkflashcards',
                        ),
                    ),
                ),
            ),
            Card(
                CardHeader(
                    CardHeaderTitle('Configuration'),
                ),
                CardContent(
                    Columns(
                        Column(
                            Label('OPENAI_API_KEY', for_='openai_api_key'),
                            PersistentInput(
                                name='openai_api_key',
                                id='openai_api_key',
                                type='password',
                                value=os.getenv('OPENAI_API_KEY', ''),
                            ),
                        ),
                        Column(
                            Label('JINA_API_KEY', for_='jina_api_key'),
                            PersistentInput(
                                name='jina_api_key',
                                id='jina_api_key',
                                type='password',
                                value=os.getenv('JINA_API_KEY', ''),
                            ),
                        ),
                    ),
                ),
            ),
            Card(
                CardHeader(
                    CardHeaderTitle('Input'),
                ),
                CardContent(
                    Columns(
                        Column(
                            Label('URL', for_='url'),
                            Input(name='url', type='text', id='url'),
                        ),
                        Column(
                            Label('File (html/pdf/epub)', for_='content'),
                            Input(
                                name='content',
                                id='content',
                                type='file',
                                multiple=False,
                                required=False,
                            ),
                        ),
                        Column(
                            Button(
                                'Fetch Text',
                                hx_post='/-/fetch-text',
                                hx_target='#text',
                                hx_swap='innerHTML',
                                hx_indicator='#fetch_spinner',
                            ),
                            Img(src='/spinner.svg', cls='htmx-indicator', id='fetch_spinner'),
                            cls='is-2',
                        ),
                        cls='is-align-items-flex-end',
                    ),
                    Div(
                        Label('Text', for_='text'),
                        Textarea(
                            name='text',
                            id='text',
                            rows=7,
                            style='font-family: monospace',
                            hx_on_change='textOnChange()',
                            hx_on__after_swap='textOnChange()',
                        ),
                    ),
                ),
            ),
            Card(
                CardHeader(
                    CardHeaderTitle('Generate Flashcards'),
                ),
                CardContent(
                    Columns(
                        Column(
                            Label('Number of flashcards to generate', for_='num_flashcards'),
                            Input(
                                name='num_flashcards',
                                id='num_flashcards',
                                type='number',
                                value=23,
                                style='width: 5em;',
                            ),
                            cls='is-3',
                        ),
                        Column(
                            Button(
                                'Generate Flashcards',
                                hx_post='/-/generate-flashcards/',
                                hx_target='#flashcards',
                                hx_swap='outerHTML',
                                hx_indicator='#generate_spinner',
                            ),
                            Img(src='/spinner.svg', cls='htmx-indicator', id='generate_spinner'),
                            cls='is-3',
                        ),
                        cls='is-align-items-flex-end',
                    ),
                    Div(
                        Label('Flashcards', for_='flashcards'),
                        Textarea(
                            name='flashcards',
                            id='flashcards',
                            rows=13,
                            style='font-family: monospace',
                        ),
                        style='margin-bottom: 1em;',
                    ),
                    Div(
                        Button('Download', id='download', hx_on_click='downloadOnClick(event)'),
                    ),
                ),
            ),
            style='margin-left: 10em; margin-right: 10em; margin-top: 5em; margin-bottom: 5em;',
        ),
        hx_encoding='multipart/form-data',
    )

serve()

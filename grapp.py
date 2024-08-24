import gradio as gr
import os

from mkflashcards import *

with open('app.js', 'r') as f:
    HEAD = '' # f'<script>{f.read()}</script>'

with gr.Blocks(head=HEAD) as mkflashcards:
    with gr.Tab('Make Flashcards'):
        openai_api_key = gr.Textbox(
            label='OPENAI_API_KEY', type='password',
            value=os.getenv('OPENAI_API_KEY', ''),
            elem_id='OPENAI_API_KEY',
        )
        with gr.Row():
            jina_api_key = gr.Textbox(
                label='JINA_API_KEY', type='password',
                value=os.getenv('JINA_API_KEY', ''),
                elem_id='JINA_API_KEY',
            )
            url = gr.Textbox(label="URL", lines=1, max_lines=1)
            fetch_btn = gr.Button("Fetch Text")
        text = gr.Textbox(label="Text", lines=7, max_lines=7)
        num_tokens = gr.Markdown('')
        with gr.Row():
            num_flashcards = gr.Number(value=23, minimum=10, maximum=1000, label="Number of flashcards to generate")
            tags = gr.Textbox(label="Tags")
            generate_btn = gr.Button("Generate Flashcards")
        output = gr.Textbox(label="Flashcards", lines=23, max_lines=123, autoscroll=False, interactive=True)
        generate_btn.click(fn=generate_flashcards, inputs=[openai_api_key, text, num_flashcards, tags], outputs=output, api_name="generate-flashcards")
        fetch_btn.click(fn=fetch_text, inputs=[url, jina_api_key], outputs=text, api_name="fetch-text")
        text.change(fn=update_num_flashcards, inputs=text, outputs=[num_flashcards, num_tokens])
    with gr.Tab('About / Instructions'):
        gr.Markdown(ABOUT)

gr.close_all()
mkflashcards.launch()

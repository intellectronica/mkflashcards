FROM python:3.12
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY mkflashcards.py .
COPY app.js .
COPY app.css .
COPY spinner.svg .
RUN touch .sesskey
RUN chmod u+w .sesskey
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]

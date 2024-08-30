FROM python:3.12
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY mkflashcards.py .
COPY app.js .
RUN touch .sesskey
RUN chmod u+w .sesskey
CMD ["python", "-m", "uvicorn", "app:app", "--port", "8080"]

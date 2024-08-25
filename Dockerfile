FROM python:3.12
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY mkflashcards.py .
COPY app.js .
CMD ["python", "app.py"]

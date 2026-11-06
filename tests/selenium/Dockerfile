FROM python:3.12-slim
WORKDIR /tests
COPY tests/selenium/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY tests/selenium/test_cases.py .
CMD ["python", "test_cases.py"]

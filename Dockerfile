FROM python:3.11-slim

WORKDIR /app

COPY main.py .
COPY start.sh .

RUN pip install --upgrade pip

RUN python -m venv /venv
RUN /venv/bin/pip install requests

RUN chmod +x start.sh

CMD ["/venv/bin/python", "start.sh"]

FROM python:3.11-slim

WORKDIR /app

COPY main.py .
COPY start.sh .

RUN pip install requests
RUN chmod +x start.sh

CMD ["./start.sh"]

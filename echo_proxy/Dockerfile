FROM python:3.11-slim

WORKDIR /app

COPY main.py .

RUN pip install fastapi httpx uvicorn colorama

EXPOSE 9090

ENV PORT=9090
ENV HOST=0.0.0.0

CMD ["python", "main.py"]
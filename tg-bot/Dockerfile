FROM python:3.9.5-slim-buster

# set work directory
WORKDIR /app

# # set env variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# install dependencies

# copy project
COPY . .
CMD ["python", "main.py"]
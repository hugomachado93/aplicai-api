FROM python:3

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
COPY ./skills2vec.model /app/skills2vec.model

RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT [ "python" ]

CMD [ "aplicai_api.py" ]
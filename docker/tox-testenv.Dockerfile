FROM qsoyq/python-tox-testenv

WORKDIR /app

RUN pip install tox poetry tox-poetry

COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock
COPY pyproxy /app/pyproxy
COPY tests /app/tests

CMD tox

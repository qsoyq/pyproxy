FROM qsoyq/python-tox-testenv

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock
COPY pyproxy /app/pyproxy
COPY tests /app/tests

CMD tox

FROM python:3.10

ENV TZ=Asia/Shanghai

RUN pip install git+https://github.com/qsoyq/pyproxy.git

CMD pyproxy

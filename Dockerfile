# syntax=docker/dockerfile:1
FROM python:3.12

WORKDIR /usr/src/app

COPY requirements.txt /usr

RUN pip install --no-cache-dir -r /usr/requirements.txt

COPY modbus-to-mqtt/ .

CMD [ "python", "./main.py" ]
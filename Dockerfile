FROM python:3.13.3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY obs-auto-rtmp.py ./

CMD [ "python", "./obs-auto-rtmp.py" ]

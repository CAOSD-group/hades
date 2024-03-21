FROM jermine/opencv:amd64-ubuntu
COPY . /app
WORKDIR /app
RUN pip3 install django python-socketio requests websocket-client
ENTRYPOINT ["python3"]
CMD ["filter_selector.py"]
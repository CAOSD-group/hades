FROM jermine/opencv:amd64-ubuntu
COPY . /app
WORKDIR /app
RUN pip3 install python-socketio requests websocket-client
ENTRYPOINT ["python3"]
CMD ["planet_tracker.py"]
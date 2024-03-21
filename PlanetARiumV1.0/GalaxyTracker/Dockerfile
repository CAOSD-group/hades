FROM jermine/opencv:amd64-ubuntu
COPY . /app
WORKDIR /app
RUN apt-get install libzbar0
RUN pip3 install python-socketio requests websocket-client pyzbar
ENTRYPOINT ["python3"]
CMD ["galaxy_tracker.py"]
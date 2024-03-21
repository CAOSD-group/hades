FROM jermine/opencv:amd64-ubuntu
COPY . /app
WORKDIR /app
RUN pip3 install requests
ENTRYPOINT ["python3"]
CMD ["feature_communicator.py"]

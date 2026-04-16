FROM ubuntu
RUN apt-get update
RUN apt-get install python3
RUN sudo apt-get install curl
ADD . /app
WORKDIR app
ENV API_KEY=sk-12345secret
EXPOSE 80 8080
ENTRYPOINT python3 app.py
CMD python3 server.py

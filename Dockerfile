FROM ubuntu:20.04
FROM python:3.9
RUN apt update
RUN apt-get install -y net-tools
RUN echo "installed net-tools"
ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD [ "sh", "entry.sh" ]
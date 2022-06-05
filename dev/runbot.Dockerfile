# syntax=docker/dockerfile:1

FROM ubuntu:20.04
WORKDIR /run_bots
RUN apt-get update && apt-get install -y python3-pip
COPY ./dev/requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . /run_bots
EXPOSE 8080
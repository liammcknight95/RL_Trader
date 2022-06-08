# syntax=docker/dockerfile:1

FROM ubuntu:20.04
WORKDIR /RL_Trader
# noninteractive avoids the install hanging on parameter input
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y python3-pip tzdata nano
# set up timezone as environment variable, the whole container is set up on that and it persists
ENV TZ="Europe/London"
COPY ./dev/requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . /RL_Trader
EXPOSE 8080
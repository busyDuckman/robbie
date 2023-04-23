#!/usr/bin/env bash

docker compose down | true
docker compose up --build -d
sleep 1
docker compose logs -f robbie_robot_tts
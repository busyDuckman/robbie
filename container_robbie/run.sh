#!/usr/bin/env bash

#docker compose down | true
#docker compose up --build -d
#sleep 1
#docker compose logs -f robbie_robot_tts

#!/bin/bash


docker compose up -d
#sleep 1
# Find the container ID
container_id_or_name=$(docker ps --format "{{.ID}}\t{{.Names}}" | grep "robbie_robot_tts" | awk '{print $1}')
# attach to the container's output; bypassing dockers interference with stdout
docker attach "$container_id_or_name"

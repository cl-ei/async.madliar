#!/usr/bin/env sh
DOCKER_NAME="async_madliar"
DOCKER_IMAGE="async_madliar_img"

docker stop ${DOCKER_NAME} 2> /dev/null
docker rm ${DOCKER_NAME} 2> /dev/null

docker run -itd --rm \
  --name ${DOCKER_NAME} \
  --net=host \
  ${DOCKER_IMAGE}

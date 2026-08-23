#!/usr/bin/env sh
DOCKER_NAME="async_madliar"
DOCKER_IMAGE="async_madliar_img"

docker stop ${DOCKER_NAME} 2> /dev/null
docker rm ${DOCKER_NAME} 2> /dev/null

docker run -itd \
  --restart=unless-stopped \
  --name ${DOCKER_NAME} \
  --net=host \
  -e APP_KEY="3.1415926" \
  -e STORAGE_ROOT="/storage_root" \
  -v /var/log:/var/log \
  -v /root/cl-service/.env:/root/.env:ro \
  -v /data/nvme/notebook_user:/storage_root \
  ${DOCKER_IMAGE}

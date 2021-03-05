#!/bin/bash

ARCH=$1

echo "gen docker stage3 for arch $ARCH"

./gentoo_get_stage_url.sh --arch $ARCH > stage3.env
. ./stage3.env

if [ -z "$ROOTFS_URL" ];then
	exit 1
fi

echo "BUILD with stage3_url=$ROOTFS_URL"
docker build --build-arg stage3_url=$ROOTFS_URL -t docker-stage3-$ARCH:latest docker_stage3 || exit $?

#echo "Installing pre-requisites"
#docker run --privileged \
#	docker-stage3-$ARCH:latest /gentoo/builder.sh $ARCH $(id -u) prereq

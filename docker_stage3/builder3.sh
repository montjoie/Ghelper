#!/bin/sh

# gentoo_docker builder step 3 (final step)
# script ran inside chroot under build user

echo "DEBUG: $0 called with $*"

ARCH=$1
USERID=$2
SRC_PATH="$3"
FDIR=$4
shift
shift
shift
shift

echo "BUILD for $ARCH as user $(id -u -n) with MAKEOPTS=$*"

echo "DEBUG: uname give $(uname -a)"

if [ -z "$ARCH" ];then
	echo "ARCH is not set"
	exit 1
fi

cd $SRC_PATH || exit $?
make $*
exit $?
#echo "DO: mrproper"
#make ARCH=$ARCH mrproper -j$NBCPU || exit $?
#echo "DO defconfig"
#make ARCH=$ARCH $DEFCONFIG -j$NBCPU KBUILD_OUTPUT=$FDIR || exit $?
#make ARCH=$ARCH modules -j$NBCPU KBUILD_OUTPUT=$FDIR || exit $?


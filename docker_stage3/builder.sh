#!/bin/sh

# gentoo_docker builder step 1
# script preparing chroot

update-binfmts --enable || exit $?

mount -t proc none /gentoo/proc || exit $?
mount --rbind /dev /gentoo/dev || exit $?
mount --rbind /sys /gentoo/sys || exit $?

ARCH=$1
if [ -z "$ARCH" ];then
	exit 1
fi

echo "CHECK binary package"
mkdir -p /gentoo/binpkgs/$ARCH || exit $?
mount -o bind /gentoo/binpkgs/$ARCH /gentoo/var/cache/binpkgs ||exit $?
find /gentoo/binpkgs

chroot /gentoo /builder2.sh $*

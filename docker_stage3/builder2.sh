#!/bin/sh

# gentoo_docker builder step 2
# script ran inside chroot

NBCPU=$(grep process /proc/cpuinfo | wc -l)
ARCH=$1
USERID=$2
SRC_PATH=$3
FDIR=$4

echo "BUILD: for $ARCH with $NBCPU cpus"

echo "MAKEOPTS=-j$NBCPU" >> /etc/portage/make.conf
emerge --info || exit $?
emerge --nospinner --quiet --color n -bk1 -v sys-devel/bc virtual/libelf || exit $?

echo "Create buildbot user with UID=$USERID"
useradd --uid $USERID buildbot || exit $?

su - buildbot -c "/builder3.sh $*"
exit $?

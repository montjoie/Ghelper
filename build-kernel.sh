#!/bin/sh

#set -e

DEBUG=0
MAKEOPTS="-j$(( $(getconf _NPROCESSORS_ONLN) + 1 ))"

if [ $# -lt 1 ]; then
	echo "Usage: $(basename $0) arch BUILD_NAME BUILD_NUMBER"
	exit 1
fi

debug() {
	if [ $DEBUG -ge 1 ];then
		echo "$*"
	fi
}

# arch must be a gentoo arch keyword
ARCH=$1
BUILD_NAME=$2
if [ -z "$BUILD_NAME" ];then
	BUILD_NAME="4.4"
fi
BUILD_NUMBER=$3
if [ -z "$BUILD_NUMBER" ];then
	BUILD_NUMBER=1
fi
BCONFIG=$(pwd)/build-config
TCONFIG=$(pwd)/toolchains
OUT="$(pwd)/out/"
FILESERVER=/var/www/fileserver/

# permit to override default
if [ -e config.ini ];then
	echo "INFO: Loading default from config.ini"
	. ./config.ini
fi

# temp hack to test all
if [ $ARCH = 'all' ];then
	for arch in $(ls $BCONFIG)
	do
		$0 $arch
	done
	exit 0
fi

# arg 1 is arch
# arg 2 is defconfig name
# arg 3 is defconfig
# arg 4 is toolchain
do_build() {
	local b_arch=$1
	local b_defconfigname=$2
	local b_defconfig=$3
	local b_toolchain=$4
	local b_dir=$5
	# verify toolchain exists
	HOST_ARCH=$(uname -m)
	if [ ! -e "$TCONFIG/$HOST_ARCH" ];then
		echo "ERROR: build not handled for host arch $HOST_ARCH"
		return 0
	fi
	if [ ! -e "$TCONFIG/$HOST_ARCH/$b_arch" ];then
		echo "ERROR: no toolchain for $b_arch"
		return 0
	fi
	if [ ! -e "$TCONFIG/$HOST_ARCH/$b_arch/$b_toolchain" ];then
		echo "ERROR: no toolchain $b_toolchain for $b_arch"
		return 0
	fi

	TOOLCHAIN_DIR="$TCONFIG/$HOST_ARCH/$b_arch/$b_toolchain"
	debug "DEBUG: found toolchain $b_toolchain in $TOOLCHAIN_DIR"
	if [ -e "$TOOLCHAIN_DIR/opts" ];then
		TC_OPTS="$(cat $TOOLCHAIN_DIR/opts)"
		MAKEOPTS="$TC_OPTS $MAKEOPTS"
	fi

	LINUX_ARCH=$b_arch
	# insert ARCH hack for name here
	case $b_arch in
	hppa)
		LINUX_ARCH=parisc
	;;
	ppc)
		LINUX_ARCH=powerpc
	;;
	ppc64)
		LINUX_ARCH=powerpc
	;;
	amd64)
		LINUX_ARCH=x86_64
	;;
	esac
	OUTPUT="$OUT/$b_arch/$b_defconfigname/$b_toolchain"
	MAKEOPTS="$MAKEOPTS ARCH=$LINUX_ARCH O=$OUTPUT INSTALL_MOD_STRIP=1"

	mkdir -p $OUTPUT

	# TODO
	cd /usr/src/linux-stable
	echo "DO: make $MAKEOPTS mrproper"
	make $MAKEOPTS mrproper > /dev/null

	echo "DO: make $MAKEOPTS $b_defconfig"
	make $MAKEOPTS $b_defconfig > $OUTPUT/build.log
	cp $OUTPUT/.config $OUTPUT/.config.old
	if [ -e "$b_dir/config" ];then
		debug "DEBUG: config hacks"
		for config in $(ls $b_dir/config)
		do
			debug "DEBUG: add config $config"
			cat $b_dir/config/$config >> $OUTPUT/.config
		done
	fi
	make $MAKEOPTS olddefconfig >> $OUTPUT/build.log
	if [ $DEBUG -ge 1 ];then
		diff -u $OUTPUT/.config.old $OUTPUT/.config
	fi

	TARGET=""
	if [ -e "$b_dir/target" ];then
		TARGET="$(cat $b_dir/target)"
		debug "DEBUG: custom target $TARGET"
	fi

	echo "DO: make $MAKEOPTS $TARGET"
	nice make $MAKEOPTS $TARGET >> $OUTPUT/build.log

	if [ -e "$b_dir/artifacts" ];then
		FDIR="$FILESERVER/$BUILD_NAME/$b_arch/$BUILD_NUMBER/$b_defconfigname/$b_toolchain/"
		mkdir -p $FDIR

		# always copy config
		cp $OUTPUT/.config $FDIR/config

		DO_MODULE=1
		grep -q 'CONFIG_MODULES=y' $OUTPUT/.config
		if [ $? -ne 0 ] ;then
			DO_MODULE=0
		fi
		if [ $DO_MODULE -eq 1 ];then
			echo "DO: install modules"
			make $MAKEOPTS modules_install INSTALL_MOD_PATH=$FDIR/modules/ >> $OUTPUT/build.log
			if [ $? -ne 0 ];then
				echo "ERROR: fail to install modules"
				return 1
			fi
			CPWD=$(pwd)
			cd $FDIR/modules/
			tar czf ../modules.tar.gz lib
			rm -r "$FDIR/modules/"
			cd $CPWD
		fi

		for fartifact in $(ls $b_dir/artifacts)
		do
			debug "DEBUG: handle artifact $fartifact"
			while read artifact
			do
				echo "INFO: copy $artifact to $FDIR"
				cp -a --dereference $OUTPUT/$artifact $FDIR/
			done < "$b_dir/artifacts/$fartifact"
		done
		chmod -R o+rX "$FILESERVER"
	fi

	# TODO clean
	return 0
}

if [ ! -e "$BCONFIG/$ARCH" ];then
	echo "ERROR: $ARCH is unsupported"
	exit 1
fi

for defconfigdir in $(ls $BCONFIG/$ARCH)
do
	echo "============================================="
	echo "INFO: $ARCH $defconfigdir"
	defconfigname=$defconfigdir
	BCDIR=$BCONFIG/$ARCH/$defconfigdir
	if [ ! -e $BCDIR/defconfig ];then
		echo "ERROR: no defconfig in $BCDIR"
		continue
	fi
	defconfig="$(cat $BCDIR/defconfig)"
	# find toolchain
	if [ ! -e "$BCDIR/toolchain" ];then
		echo "ERROR: no toolchain in $BCDIR"
		continue
	fi
	for toolchain in $(ls $BCDIR/toolchain)
	do
		debug "DEBUG: use toolchain $toolchain"
		do_build $ARCH $defconfigname $defconfig $toolchain $BCDIR
		if [ $? -ne 0 ];then
			echo "ERROR"
		fi
	done
done

exit 0

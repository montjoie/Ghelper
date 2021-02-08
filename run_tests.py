#!/usr/bin/env python3

"""
    boot a gentoo artifact directory
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
import time
import xmlrpc.client
import yaml
import jinja2


###############################################################################
###############################################################################
def boot():
    relpath = "%s/%s/%s/%s/%s" % (args.buildname, args.arch, args.buildnumber, args.defconfig, args.toolchain)
    kdir = "%s/%s" % (tc["config"]["fileserver"], relpath)
    cachedir = os.path.expandvars(tc["config"]["cache"])

    arch_endian = None

    if os.path.exists("%s/config" % kdir):
        kconfig = open("%s/config" % kdir)
        kconfigs = kconfig.read()
        kconfig.close()
        if re.search("CONFIG_CPU_BIG_ENDIAN=y", kconfigs):
            endian = "big"
        else:
            endian = "little"
        if re.search("CONFIG_PARISC=", kconfigs):
            arch = "parisc"
            arch_endian = "hppa"
            qarch = "hppa"
            larch = "parisc"
        if re.search("CONFIG_M68K=", kconfigs):
            arch = "m68k"
            arch_endian = "m68k"
            qarch = "m68k"
            larch = "m68k"
        if re.search("CONFIG_SPARC32=", kconfigs):
            arch = "sparc"
            arch_endian = "sparc"
            qarch = "sparc"
            larch = "sparc"
        if re.search("CONFIG_SPARC64=", kconfigs):
            arch = "sparc64"
            arch_endian = "sparc64"
            qarch = "sparc64"
            larch = "sparc"
        if re.search("CONFIG_ARM=", kconfigs):
            arch = "arm"
            qarch = "arm"
            if re.search("CONFIG_CPU_BIG_ENDIAN=y", kconfigs):
                arch_endian = "armbe"
                qarch = "unsupported"
            else:
                arch_endian = "armel"
            larch = "arm"
        if re.search("CONFIG_ARM64=", kconfigs):
            arch = "arm64"
            qarch = "aarch64"
            if re.search("CONFIG_CPU_BIG_ENDIAN=y", kconfigs):
                arch_endian = "arm64be"
            else:
                arch_endian = "arm64"
            larch = "arm64"
        if re.search("CONFIG_MIPS=", kconfigs):
            if re.search("CONFIG_64BIT=y", kconfigs):
                arch = "mips64"
                qarch = "mips64"
                if endian == 'big':
                    arch_endian = "mips64be"
                else:
                    arch_endian = 'mips64el'
            else:
                arch = "mips"
                qarch = "mips"
                if endian == 'big':
                    arch_endian = "mipsbe"
                else:
                    arch_endian = 'mipsel'
                    qarch = "mipsel"
            larch = "mips"
        if re.search("CONFIG_ALPHA=", kconfigs):
            arch = "alpha"
            arch_endian = "alpha"
            qarch = "alpha"
            larch = "alpha"
        if re.search("CONFIG_PPC=", kconfigs):
            arch = "powerpc"
            arch_endian = "powerpc"
            qarch = "ppc"
            larch = "powerpc"
        if re.search("CONFIG_PPC64=", kconfigs):
            arch = "powerpc64"
            arch_endian = "ppc64"
            qarch = "ppc64"
            larch = "powerpc"
        if re.search("CONFIG_S390=", kconfigs):
            arch = "s390"
            arch_endian = "s390"
            qarch = "s390x"
            larch = "s390"
        if re.search("CONFIG_X86_64=", kconfigs):
            arch = "x86_64"
            arch_endian = "x86_64"
            qarch = "x86_64"
            larch = "x86_64"
        if re.search("CONFIG_X86=", kconfigs) and not re.search("CONFIG_X86_64=", kconfigs):
            arch = "x86"
            arch_endian = "x86"
            qarch = "i386"
            larch = "x86"
    else:
        print("ERROR: no config in %s" % kdir)
        return 1

    if arch_endian is None:
        print("ERROR: Missing endian arch")
        return 1

    print("INFO: arch is %s, Linux arch is %s, QEMU arch is %s, archendian is %s" % (arch, larch, qarch, arch_endian))

    for device in t["templates"]:
        if "devicename" in device:
            devicename = device["devicename"]
        else:
            devicename = device["devicetype"]
        if "larch" in device:
            device_larch = device["larch"]
        else:
            device_larch = device["arch"]
        if device_larch != larch:
            if args.debug:
                print("SKIP: %s (wrong larch %s vs %s)" % (devicename, device_larch, larch))
            continue
        if device["arch"] != arch:
            if args.debug:
                print("SKIP: %s device arch: %s vs arch=%s" % (devicename, device["arch"], arch))
            continue
        print("==============================================")
        print("CHECK: %s" % devicename)
        # check config requirements
        skip = False
        if "configs" in device and device["configs"] is not None and kconfigs != "":
            for config in device["configs"]:
                if "name" not in config:
                    print("Invalid config")
                    print(config)
                    continue
                if not re.search(config["name"], kconfigs):
                    if "type" in config and config["type"] == "mandatory":
                        print("\tSKIP: missing %s" % config["name"])
                        skip = True
                    else:
                        print("\tINFO: missing %s" % config["name"])
                else:
                    if args.debug:
                        print("DEBUG: found %s" % config["name"])
        if skip:
            continue
        goodtag = True
        if args.dtag:
            for tag in args.dtag.split(","):
                if "devicename" in device and tag == device["devicename"]:
                    tagfound = True
                    continue
                if tag == device["devicetype"]:
                    tagfound = True
                    continue
                if args.debug:
                    print("DEBUG: check tag %s" % tag)
                if "tags" not in device:
                    print("SKIP: no tag")
                    gootdtag = False
                    continue
                tagfound = False
                for dtag in device["tags"]:
                    if tag == "qemu":
                        if "qemu" in device:
                            tagfound = True
                    if tag == "noqemu":
                        if "qemu" not in device:
                            tagfound = True
                    if args.debug:
                        print("DEBUG: found device tag %s" % dtag)
                    if dtag == tag:
                        tagfound = True
                if not tagfound:
                    print("SKIP: cannot found tag %s" % tag)
                    goodtag = False
        if not goodtag:
            continue
        kerneltype = "image"
        kernelfile = device["kernelfile"]
        if kernelfile == "zImage":
            kerneltype = "zimage"
        if kernelfile == "uImage":
            kerneltype = "uimage"
        # check needed files
        if "kernelfile" not in device:
            print("ERROR: missing kernelfile")
            continue
        if args.debug:
            print("DEBUG: seek %s" % device["kernelfile"])
        kfile = "%s/%s" % (kdir, device["kernelfile"])
        if os.path.isfile(kfile):
            if args.debug:
                print("DEBUG: found %s" % kfile)
        else:
            print("SKIP: no kernelfile %s in %s" % (device["kernelfile"], kdir))
            continue
        # Fill lab indepedant data
        jobdict = {}
        jobdict["KERNELFILE"] = kernelfile
        with open(kfile, "rb") as fkernel:
            jobdict["KERNEL_SHA256"] = hashlib.sha256(fkernel.read()).hexdigest()
        jobdict["DEVICETYPE"] = device["devicetype"]
        jobdict["MACH"] = device["mach"]
        jobdict["ARCH"] = device["arch"]
        jobdict["ARCHENDIAN"] = arch_endian
        jobdict["KENDIAN"] = endian
        jobdict["KERNELTYPE"] = kerneltype
        jobdict["PATH"] = relpath

        if "console_device" in device:
            jobdict["console_device"] = device["console_device"]

        jobdict["JOBNAME"] = "Gentoo test %s %s %s %s %s" % (args.buildname, args.buildnumber, args.arch, args.defconfig, args.toolchain)
        for dtag in device["tags"]:
            if dtag == "notests" or dtag == "nostorage" or args.testsuite is None:
                jobdict["test"] = "False"
                if args.debug:
                    print("DEBUG: Remove test from job")
        # test are still enabled check testsuite
        if args.testsuite is not None:
            for testsuite in args.testsuite.split(','):
                print("DEBUG: enable test %s" % testsuite)
                jobdict["test_%s" % testsuite] = 'True'
        if "qemu" in device:
            if qarch == "unsupported":
                print("Qemu does not support this")
                continue
            print("\tQEMU")
            jobdict["qemu_arch"] = qarch
            if "netdevice" in device["qemu"]:
                jobdict["qemu_netdevice"] = device["qemu"]["netdevice"]
            if "model" in device["qemu"]:
                jobdict["qemu_model"] = device["qemu"]["model"]
            if "no_kvm" in device["qemu"]:
                jobdict["qemu_no_kvm"] = device["qemu"]["no_kvm"]
            if "machine" in device["qemu"]:
                jobdict["qemu_machine"] = device["qemu"]["machine"]
            if "cpu" in device["qemu"]:
                jobdict["qemu_cpu"] = device["qemu"]["cpu"]
            if "memory" in device["qemu"]:
                jobdict["qemu_memory"] = device["qemu"]["memory"]
            if "console_device" in device["qemu"]:
                jobdict["console_device"] = device["qemu"]["console_device"]
            if "guestfs_interface" in device["qemu"]:
                jobdict["guestfs_interface"] = device["qemu"]["guestfs_interface"]
            if "guestfs_driveid" in device["qemu"]:
                jobdict["guestfs_driveid"] = device["qemu"]["guestfs_driveid"]
            if "extra_options" in device["qemu"]:
                jobdict["qemu_extra_options"] = device["qemu"]["extra_options"]
                # with root on nfs/nbd, tests are not set on a storage, so we need to filter them
                if args.testsuite is None:
                    newextrao = []
                    for extrao in device["qemu"]["extra_options"]:
                        if re.search("lavatest", extrao):
                            continue
                        newextrao.append(extrao)
                    jobdict["qemu_extra_options"] = newextrao
            if "extra_options" not in device["qemu"]:
                jobdict["qemu_extra_options"] = []
            if "smp" in device["qemu"]:
                jobdict["qemu_extra_options"].append("-smp cpus=%d" % device["qemu"]["smp"])
            netoptions = "ip=dhcp"
            jobdict["qemu_extra_options"].append("-append '%s %s'" % (device["qemu"]["append"], netoptions))
        templateLoader = jinja2.FileSystemLoader(searchpath=templatedir)
        templateEnv = jinja2.Environment(loader=templateLoader)
        template = templateEnv.get_template("gentoo.jinja2")

        # now try to boot on LAVA
        for lab in tlabs["labs"]:
            send_to_lab = False
            print("\tCheck %s on %s" % (devicename, lab["name"]))
            if "disabled" in lab and lab["disabled"]:
                continue
            server = xmlrpc.client.ServerProxy(lab["lavauri"])
            devlist = server.scheduler.devices.list()
            # TODO check device state
            for labdevice in devlist:
                if labdevice["type"] == device["devicetype"]:
                    send_to_lab = True
            if not send_to_lab:
                print("\tSKIP: not found")
                continue
            if "dtb" in device:
                jobdict["DTB"] = device["dtb"]
                dtbfile = "%s/%s" % (kdir, device["dtb"])
                if not os.path.isfile(dtbfile):
                    print("SKIP: no dtb at %s" % dtbfile)
                    continue
                with open(dtbfile, "rb") as fdtb:
                    jobdict["DTB_SHA256"] = hashlib.sha256(fdtb.read()).hexdigest()
            # TODO modules could not exists if CONFIG_MODULES is not set
            # modules.tar.gz
            with open("%s/modules.tar.gz" % kdir, "rb") as fmodules:
                jobdict["MODULES_SHA256"] = hashlib.sha256(fmodules.read()).hexdigest()

            jobdict["BOOT_FQDN"] = args.fileserver
            result = subprocess.check_output("./gentoo_get_stage_url.sh --arch %s --cachedir %s" % (arch_endian, cachedir), shell=True)
            for line in result.decode("utf-8").split("\n"):
                what = line.split("=")
                if what[0] == 'ROOTFS_PATH':
                    jobdict["rootfs_path"] = what[1]
                if what[0] == 'ROOTFS_BASE':
                    jobdict["ROOT_FQDN"] = what[1]
                if what[0] == 'ROOTFS_SHA512':
                    jobdict["rootfs_sha512"] = what[1]
                if what[0] == 'PORTAGE_URL':
                    jobdict["portage_url"] = what[1]
            jobdict["auto_login_password"] = 'bob'
            jobdict["test_gentoo"] = "True"
            jobdict["rootfs_path"] = jobdict["rootfs_path"].replace("__ARCH_ENDIAN__", arch_endian).replace("__ARCH__", arch)

            if re.search("gz$", jobdict["rootfs_path"]):
                jobdict["ROOTFS_COMP"] = "gz"
            if re.search("xz$", jobdict["rootfs_path"]):
                jobdict["ROOTFS_COMP"] = "xz"
            if re.search("bz2$", jobdict["rootfs_path"]):
                jobdict["ROOTFS_COMP"] = "bz2"

            # by default the RAMDISK URI is the same as ROOT
            jobdict["RAMD_FQDN"] = jobdict["ROOT_FQDN"]

            jobt = template.render(jobdict)
            fw = open("%s/job-%s.yaml" % (cachedir, devicename), "w")
            fw.write(jobt)
            fw.close()

            if not args.noact:
                jobid = server.scheduler.jobs.submit(jobt)
                print(jobid)
                if lab["name"] not in boots:
                    boots[lab["name"]] = {}
                boots[lab["name"]][jobid] = {}
                boots[lab["name"]][jobid]["devicename"] = devicename
            else:
                print("\tSKIP: send job to %s" % lab["name"])
    return 0

###############################################################################
###############################################################################

arch = None
boots = {}
templatedir = os.getcwd()
startdir = os.getcwd()
dtemplates_yaml = "all.yaml"
labs_yaml = "labs.yaml"

os.environ["LC_ALL"] = "C"
os.environ["LC_MESSAGES"] = "C"
os.environ["LANG"] = "C"

parser = argparse.ArgumentParser()
parser.add_argument("--noact", "-n", help="No act", action="store_true")
parser.add_argument("--quiet", "-q", help="Quiet, do not print build log", action="store_true")
parser.add_argument("--dtag", "-D", type=str, help="Select device via some tags")
parser.add_argument("--testsuite", type=str, help="Comma separated list of testss to do", default = None)
parser.add_argument("--debug", "-d", help="increase debug level", action="store_true")
parser.add_argument("--waitforjobsend", "-W", help="Wait until all jobs ended", action="store_true")
parser.add_argument("--arch", type=str, help="Gentoo arch", required=True)
parser.add_argument("--buildname", type=str, help="buildbot build name", required=True)
parser.add_argument("--buildnumber", type=str, help="buildbot buildnumber", required=True)
parser.add_argument("--defconfig", type=str, help="The defconfig name", required=True)
parser.add_argument("--toolchain", type=str, help="The toolchain name", required=True)
parser.add_argument("--fileserver", type=str, help="An URL to the base fileserver", required=True)
args = parser.parse_args()

try:
    tcfile = open("config.yaml")
except IOError:
    print("ERROR: Cannot open config file")
    sys.exit(1)
tc = yaml.safe_load(tcfile)

if "config" not in tc:
    print("ERROR: invalid config file")
    sys.exit(1)

try:
    tfile = open(dtemplates_yaml)
except IOError:
    print("ERROR: Cannot open device template config file: %s" % dtemplates_yaml)
    sys.exit(1)
t = yaml.safe_load(tfile)

try:
    tlabsfile = open(labs_yaml)
except IOError:
    print("ERROR: Cannot open labs config file: %s" % labs_yaml)
    sys.exit(1)
tlabs = yaml.safe_load(tlabsfile)

cachedir = os.path.expandvars(tc["config"]["cache"])
if not os.path.isdir(cachedir):
    os.mkdir(cachedir)

boot()

os.chdir(startdir)

# We should have generated at least one job
if len(boots) == 0 and not args.noact:
    sys.exit(1)

if len(boots) > 0 and args.waitforjobsend:
    all_jobs_ended = False
    all_jobs_success = True
    while not all_jobs_ended:
        time.sleep(60)
        all_jobs_ended = True
        for labname in boots:
            for lab in tlabs["labs"]:
                if lab["name"] == labname:
                    break;
            #print("DEBUG: Check %s with %s" % (labname, lab["lavauri"]))
            server = xmlrpc.client.ServerProxy(lab["lavauri"], allow_none=True)
            for jobid in boots[labname]:
                try:
                    jobd = server.scheduler.jobs.show(jobid)
                    if jobd["state"] != 'Finished':
                        all_jobs_ended = False
                        print("Wait for job %d" % jobid)
                        print(jobd)
                    else:
                        boots[labname][jobid]["health"] = jobd["health"]
                        boots[labname][jobid]["state"] = jobd["state"]
                        if jobd["health"] != 'Complete':
                            all_jobs_success = False
                except OSError as e:
                    print(e)
                except TimeoutError as e:
                    print(e)
    if not all_jobs_success:
        sys.exit(1)

sys.exit(0)

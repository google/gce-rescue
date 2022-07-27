#!/bin/bash
# Automatic disk discovery - Jun 2022 - @halleysouza

disk=GOOGLE_DISK_NAME

# Set different hostname to avoid confusion
sed -i "s/$(hostname)/$(hostname)-rescue/g" /etc/hosts
hostname ${HOSTNAME}-rescue

# Watching for the secondary disk
while [ true ]; do
    [[ -e /dev/disk/by-id/google-${disk} ]] && {
        mkdir -p /mnt/sysroot
        fdisk -l /dev/disk/by-id/google-${disk} | grep Linux\ filesystem | awk '{ system("mount "$1" /mnt/sysroot") }'
        # Let's prepare chroot
        [[ -d /mnt/sysroot/proc ]] && mount -t proc proc /mnt/sysroot/proc
        [[ -d /mnt/sysroot/sys ]] && mount -t sysfs sys /mnt/sysroot/sys
        [[ -d /mnt/sysroot/dev ]] && mount -o bind /dev /mnt/sysroot/dev
        exit 0
    }
    sleep 5
done


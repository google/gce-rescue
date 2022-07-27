import sys
import logging
import googleapiclient.discovery 
from gce_rescue.rescue import InitInstance, attach_disk, backup, create_rescue_disk, delete_rescue_disk, detach_disk, set_metadata, start_instance, stop_instance

# logging.basicConfig(level=logging.DEBUG)


def set_rescue_mode(vm: InitInstance, disk_name: str, device_name: str) -> None:
    """
    Set instance to boot as Rescue Mode.
    This is like that just for tests purposes - please dont judge me (1)
    """
    print(1)
    stop_instance(vm) # STOP INSTANCE
    print(2)
    backup(vm, disk=disk_name) # BACKUP
    print(3)
    create_rescue_disk(vm, source_disk=vm.rescue_source_disk) # CREATE RESCUE DISK
    print(4)
    detach_disk(vm, disk=device_name) # DETACH BOOT DISK
    print(5)
    attach_disk(vm, disk_name=vm.rescue_disk, device_name=vm.rescue_disk, boot=True) # ATTACH DISK RESCUE DISK (BOOT)
    print(6)
    set_metadata(vm, disk=device_name) # SET METADATA
    print(7)
    start_instance(vm) # START INSTANCE
    print(8)
    attach_disk(vm, disk_name=disk_name, device_name=device_name, boot=False) # ATTACH DISK (SECONDARY)
    print("Done")


def reset_rescue_mode(vm: InitInstance, disk_name: str, device_name: str) -> None:
    """
    Reset instance to the original boot mode.
    This is like that just for tests purposes - please dont judge me (2)
    """
    print(1)
    stop_instance(vm) # STOP INSTANCE
    print(2)
    detach_disk(vm, disk=vm.rescue_source_disk) # DETACH BOOT DISK
    print(3)
    detach_disk(vm, disk=device_name) # DETACH BOOT DISK (SECONDARY)
    print(4)
    attach_disk(vm, disk_name=disk_name, device_name=device_name, boot=True) # ATTACH DISK ORIGINAL DISK (BOOT)
    print(5)
    set_metadata(vm, disk=device_name) # RESET METADATA BACK
    print(6)
    start_instance(vm) # START INSTANCE
    print(7)
    delete_rescue_disk(vm, disk_name=vm.rescue_source_disk) # CLEAN UP UNUSED RESCUE DISK
    print("Done")


def main(argv):
    # TODO: Some argv here
    # Initiate the Goolge API Client Discovery API.
    compute = googleapiclient.discovery.build('compute', 'v1')

    # For tests purposes...
    vm_rescue = InitInstance(
        compute = compute,
        project = "gce-rescue-mode",
        zone = "europe-central2-a",
        instance = "test"
    )

    for disk in vm_rescue.instance_data["disks"]:
        if disk["boot"] == True:
            device_name = disk["deviceName"]
            source = disk["source"]  
            disk_name = source.split("/")[-1] # Ie: https://www.googleapis.com/compute/v1/projects/gce-rescue-mode/zones/europe-central2-a/disks/linux

    set_rescue_mode(vm_rescue, disk_name=disk_name, device_name=device_name)
            

if __name__ == '__main__':
    main(sys.argv)

from dataclasses import dataclass, field
from typing import Callable, Dict
import logging

import googleapiclient.errors

from gce_rescue.config import get_config
from gce_rescue.utils import validate_instance_mode, wait_for_operation

_logger = logging.getLogger(__name__)

def get_instance_info(compute: Callable, instance: str, project_data: Dict[str, str]) -> Dict:
    '''
    Set Dictionary with complete data from instances().get() from the instance.
    https://cloud.google.com/compute/docs/reference/rest/v1/instances/get

    Attributes:
        compute: obj, API Object
        instance: str, Instace name
        project_data: dict, Dictionary containing project and zone keys to be unpacked when calling the API.
    '''
    return compute.instances().get(
        **project_data, 
        instance = instance).execute()

@dataclass
class InitInstance:
    compute: Callable
    project: str
    zone: str
    instance: str
    instance_data: str = field(init=False)
    ts: int = field(init=False)
    _instance_status: str = ""
    _rescue_source_disk: str = ""
    _rescue_mode_status: Dict = field(default_factory=lambda: ({}))

    def __post_init__(self):
        self.instance_data = get_instance_info(
            compute = self.compute, 
            instance = self.instance,
            project_data = self.project_data)

        self._rescue_mode_status = validate_instance_mode(self.instance_data)
        self.ts = self._rescue_mode_status['ts']

        self._instance_status = self.instance_data["status"]
        self._rescue_source_disk = get_config('source_guests')[0] # Using the Debian10 as default image.

    @property
    def rescue_mode_status(self) -> Dict:
        return self._rescue_mode_status

    @property
    def project_data(self) -> str:
        return { 'project': self.project, 'zone': self.zone }

    @property
    def rescue_disk(self) -> str:
        return f"linux-rescue-disk-{self.ts}"

    @property
    def instance_status(self) -> str:
        return self._instance_status

    @instance_status.setter
    def instance_status(self, v: str) -> None:
        self._instance_status = v

    @property
    def rescue_source_disk(self) -> str:
        return self._rescue_source_disk

    @rescue_source_disk.setter
    def rescue_source_disk(self, v: str) -> None:
        self._rescue_source_disk = v


    def _pre_validation(self) -> bool:
        """
        Pre validation check list before to continue:
            a. IAM Permission list
            b. Services enabled (compute.googleapis.com, storage.googleapis.com, etc.)

        Returns:
            a. True if its ok
            b. raise execeptions for failed checks
        """
        pass


def guess_guest(instance: InitInstance) -> str:
    """
    Determined which Guest OS Family is being used and select a different OS for recovery disk.
    Default: projects/debian-cloud/global/images/family/debian-10
    """
    _guests = get_config("source_guests")
    pass

def start_instance(vm: InitInstance) -> Dict:
    """
    Start instance: https://cloud.google.com/compute/docs/reference/rest/v1/instances/start
    Returns:
        operation-result: Dict
    """
    _logger.info(f"Starting {vm.instance}...")

    if vm.instance_status == "RUNNING":
        _logger.info(f"{vm.instance} is already runnning.")
        return {}
    operation = vm.compute.instances().start(
            **vm.project_data,
            instance = vm.instance).execute()

    result = wait_for_operation(vm, oper=operation)
    if result["status"] == 'DONE':
        vm.instance_status = "RUNNING"
        return result

    raise Exception(result)

def stop_instance(vm: InitInstance) -> Dict:
    """
    Stop instance: https://cloud.google.com/compute/docs/reference/rest/v1/instances/stop
    Returns:
        operation-result: Dict
    """
    _logger.info(f"Stopping {vm.instance}...")

    if vm.instance_status == "TERMINATED":
        _logger.info(f"{vm} is already stopped.")
        return {}
    operation = vm.compute.instances().stop(
            **vm.project_data,
            instance = vm.instance).execute()

    result = wait_for_operation(vm, oper=operation)
    if result["status"] == 'DONE':
        vm.instance_status = "TERMINATED"
        return result

    raise Exception(result)


def backup(vm: InitInstance, disk: str) -> Dict:
    """
        a. Save the original status of instance_data. (where?)
        b. Save original startup_script, if exists
        c. Create a snaphost of the instance boot disk, adding self._ts to the disk name.
           https://cloud.google.com/compute/docs/reference/rest/v1/disks/createSnapshot

    Param:
        disk: str, The failed disk name
    Returns:
        operation-result: Dict
    """
    
    _snapshot_name = f"{disk}-{vm.ts}"
    _snapshot_body = {
        "name": _snapshot_name
    }

    _logger.info(f"Creating snapshot {_snapshot_name}... ")

    operation = vm.compute.disks().createSnapshot(
        **vm.project_data,
        disk = disk,
        body = _snapshot_body).execute()

    result = wait_for_operation(vm, oper=operation)
    if result["status"] == 'DONE':
        return result

    raise Exception(result)

def set_metadata(vm: InitInstance, disk: str) -> Dict:
    """
    Configure Instance custom metadata.
    https://cloud.google.com/compute/docs/reference/rest/v1/instances/setMetadata
        a. Set rescue-mode=<ts unique id> if disable=False
        b. Delete rescue-mode if disable=True
        c. Replace startup-script with local startup-script.sh content.

    Params:
        disk: str, Device Name to be mounted as secundary disk under /mnt/sysroot
    Returns:
        operation-result: Dict
    """
    _startup_script_file = get_config("startup-script-file")

    with open(_startup_script_file, "r") as file: 
        _file_content = file.read()
        _file_content = _file_content.replace("GOOGLE_DISK_NAME", disk)

    _metadata_body = {
        'fingerprint': vm.instance_data['metadata']['fingerprint'],
        'items': [
            { 'key': 'startup-script', 'value': _file_content },
            { 'key': 'rescue-mode', 'value': vm.ts }
        ]
    }

    _logger.info(f"Setting custom metadata...")
    operation = vm.compute.instances().setMetadata(
        **vm.project_data,
        instance = vm.instance,
        body = _metadata_body).execute()

    result = wait_for_operation(vm, oper=operation)
    if result["status"] == 'DONE':
        return result

    raise Exception(result)

def create_rescue_disk(vm: InitInstance, source_disk: str) -> Dict:
    """
    Create new temporary rescue disk based on source_disk.
    https://cloud.google.com/compute/docs/reference/rest/v1/disks/insert
    Returns:
        operation-result: Dict
    """

    chk_disk_exist = {}

    try:
        chk_disk_exist = vm.compute.disks().get(
            **vm.project_data,
            disk = vm.rescue_disk).execute()
    except googleapiclient.errors.HttpError as e:
        if e.status_code == 404:
            _logger.info(f"Disk not found. Creating rescue disk {vm.rescue_disk}...")
        else:
            raise Exception(e)


    if "name" in chk_disk_exist.keys():
        if "users" in chk_disk_exist.keys():
            raise Exception(f"Disk {vm.rescue_disk} is currently in use: {chk_disk_exist['users']}")

        _logger.info(f"Disk {vm.rescue_disk} already exist. Skipping...")
        return {}

    disk_body = {
        'name': vm.rescue_disk,
        'sourceImage': source_disk,
        'type': f"projects/{vm.project}/zones/{vm.zone}/diskTypes/pd-balanced"
    }

    operation = vm.compute.disks().insert(
        **vm.project_data,
        body = disk_body).execute()

    result = wait_for_operation(vm, oper=operation)
    if result["status"] == 'DONE':
        return result

    raise Exception(result)

def delete_rescue_disk(vm: InitInstance, disk_name: str) -> Dict:
    """
    Delete rescue disk after resetting the instance to the original configuration.
    https://cloud.google.com/compute/docs/reference/rest/v1/disks/delete
    Param:
        disk_name: str, Name of the disk to be deleted.
    Returns:
        operation-result: Dict
    """

    _logger.info(f"Deleting disk {disk_name}...")
    operation = vm.compute.disks().delete(
        **vm.project_data,
        disk = disk_name).execute()

    result = wait_for_operation(vm, oper=operation)
    if result["status"] == "DONE":
        return result

    raise Exception(result)


def attach_disk(vm: InitInstance, disk_name: str, device_name: str, boot: bool = False) -> Dict:
    """
    Attach disk on the instance. By default (boot=False) it will attach as secundary
    https://cloud.google.com/compute/docs/reference/rest/v1/instances/attachDisk
    Returns:
        operation-result: Dict
    """
    
    attach_disk_body = {
        "boot": boot,
        "name": disk_name,
        "deviceName": device_name,
        "type": "PERSISTENT",
        "source": f"projects/{vm.project}/zones/{vm.zone}/disks/{disk_name}"
    }

    _logger.info(f"Attaching disk {disk_name}...")
    operation = vm.compute.instances().attachDisk(
        **vm.project_data,
        instance = vm.instance,
        body = attach_disk_body).execute()

    result = wait_for_operation(vm, oper=operation)
    if result["status"] == 'DONE':
        return result

    raise Exception(result)
  

def detach_disk(vm: InitInstance, disk: str) -> Dict:
    """
    Detach disk from the instance.
    https://cloud.google.com/compute/docs/reference/rest/v1/instances/detachDisk
    Returns:
        operation-result: Dict
    """
    
    _logger.info(f"Detaching disk {disk} from {vm.instance}...")
    operation = vm.compute.instances().detachDisk(
        **vm.project_data,
        instance = vm.instance,
        deviceName = disk).execute()

    result = wait_for_operation(vm, oper=operation)
    if result["status"] == 'DONE':
        return result

    raise Exception(result)


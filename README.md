# GCE Rescue # 

The core idea is to make analogies to the steps taken to rescue a physical instance, where a rescue boot disk is plugged into the machine, changing the order of the boot disks and using the faulty disk as secondary.

Once the user is in rescue mode, they can take the steps necessary to change/restore any configuration on the target disk. This script will attempt to automount the faulty disk in /mnt/sysroot.

At the end, the user runs this script again to restore the configuration to boot from the original (now recovered) disk.

The main advantage to using this approach, rather than creating a 2nd instance, is to make use of the resources already configured for the VM, such as networking, VPC firewalls and routes, policies, permissions, etc.

> IMPORTANT: *This is not an officially supported Google product.*
> Note that this is not an officially supported Google product, but a community effort. The Google Cloud Support team maintains this code and we do our best to avoid causing any problems in your projects, but we give no guarantees to that end.


## Instalation ##

```
$ git clone <repo url>
$ cd gce-rescue/
$ python3 -m pip install -r requirements.txt
```

## Authentication ##

This script make use of ADC via gcloud to authenticate. Make sure you have gcloud installed and your ADC updated.

```
$ gcloud auth application-default login
```

## Usage ##

```
$ ./gce-rescue.py --help

       USAGE: ./gce-rescue.py [flags]
flags:

./gce-rescue.py:
  --[no]debug: Print to the log file in debug level.
    (default: 'false')
  --[no]force: Don't ask for confirmation.
    (default: 'false')
  --instance: Instance name.
  --project: The project-id that has the instance.
  --zone: Zone where the instance is created.
  
Try --helpfull to get a list of all flags.
```

- ### --zone ### 
  - The instances zone. (REQUIRED)
- ### --instance ###
  - The instance name (not instance ID). (REQUIRED)
- ### --project ###
  - The project-id of the faulty instance. (OPTIONAL)
- ### --force ###
  - Do not ask for confirmation. It can be useful when running from a script.
- ### --debug ###
  - If provided, the log output will be set to DEBUG level. (OPTIONAL)
  - The log file will be created on ./ containing the VM name and timestamp on the name, that can be used to help to troubleshoot failed executions as well as to manually recover the instance's original configuration, if necessary.


> The log files contain important information about the initial state of the VM that may be required to manually restore it.


## Permissions ##

This is the list of the minimal IAM permissions required.

| Description | Permissions|
|----------:|----------|
| Start and stop instance | compute.instances.stop <br/> compute.instances.start |
| Create and remove disk | compute.instances.attachDisk on the instance <br/> compute.instances.detachDisk on the instance <br/> compute.images.useReadOnly on the image if creating a new root persistent disk <br/> compute.disks.use on the disk if attaching an existing disk in read/write mode  <br/> compute.disks.setLabels on the disk if setting labels |
| Create snapshot | compute.snapshots.create on the project <br/> compute.disks.createSnapshot on the disk |
| Configure metadata | compute.instances.setMetadata if setting metadata  <br/> compute.instances.setLabels on the instance if setting labels |


## Contact ##
gce-rescue-dev@google.com


 

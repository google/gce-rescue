#
# Static values

config = {
    'verbosity': 'info',
    'startup-script-file': 'gce_rescue/startup-script.sh',
    'source_guests': (
        'projects/debian-cloud/global/images/family/debian-10',
        'projects/rocky-linux-cloud/global/images/rocky-linux-8',
        'projects/ubuntu-os-cloud/global/images/ubuntu-2004-lts'
    ),
}


def get_config(key):
    if key in config.keys():
        return config[key]

import requests
import datetime
import json
from paramiko import SSHClient
from scp import SCPClient

ntsclIP = ["192.168.58.11", "192.168.58.10"]
username = 'nsbackup'
oldest_backup_name = ""

def get_password():
    url = "https://192.168.59.21/netscaler_backup"
    response = requests.request("GET", url, headers=None, verify=False)
    return response.content.decode()


password = get_password()


def create_backup(mgmt_ip):
    # Create and download backup file with level full and name constructed out of mgmt IP and date in yyyy-mm-dd format.

    url = "http://" + mgmt_ip + "/nitro/v1/config/systembackup?action=create"
    filename = "" + mgmt_ip + "_" + datetime.date.today().strftime('%Y-%m-%d')

    payload = json.dumps({
        "systembackup": {
            "filename": filename,
            "level": "full"
        }
    })

    headers = {
        'X-NITRO-USER': username,
        'X-NITRO-PASS': password,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        print('Backup created on ' + mgmt_ip)
        download_backup_file(mgmt_ip, filename)

    else:
        data = response.json()
        err_mess = data['message']
        print("" + str(response.status_code) + " Nitro Error: " + err_mess)


def download_backup_file(mgmt_ip, name):
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.connect(mgmt_ip, 22, username, password, None, None, 10.0)
    with SCPClient(ssh.get_transport()) as scp:
        scp.get("/var/ns_sys_backup/" + name + ".tgz", "/Users/yevhenii/PycharmProjects/nsBackup")


def get_backups_count(mgmt_ip):
    # Get the summary of the backup files. If there are 50 of them - delete the oldest one

    url = "http://" + mgmt_ip + "/nitro/v1/config/systembackup?view=summary"
    headers = {
        'X-NITRO-USER': username,
        'X-NITRO-PASS': password
    }

    response = requests.request("GET", url, headers=headers, data=None)
    data = response.json()

    amount_of_backups = 0
    for item in data['systembackup']:
        amount_of_backups = amount_of_backups + 1

    global oldest_backup_name
    oldest_backup_name = data['systembackup'][0]['filename']

    return amount_of_backups


def delete_oldest_backup(mgmt_ip):


    url = "http://" + mgmt_ip + "/nitro/v1/config/systembackup/" + oldest_backup_name

    headers = {
        'X-NITRO-USER': username,
        'X-NITRO-PASS': password
    }

    response = requests.request("DELETE", url, headers=headers, data=None)
    if response.status_code == 200:
        print('Deleted the backup:' + oldest_backup_name)


for ip in ntsclIP:
    try:
        if get_backups_count(ip) == 50:
            print('Removing the oldest backup')
            delete_oldest_backup(ip)

        create_backup(ip)

    except Exception as e:
        print(e)
        print('\r\n')

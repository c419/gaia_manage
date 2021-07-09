#!/usr/bin/env python
"""
Simple module to control VirtualBox VM.
"""
from subprocess import run
import logging
import re
import time

class VM:
    """
    Class represents a local VirtualBox VM
    __init__(name) 
        Creates an instance used to control VM. Raises error if there is no such VM
    """
    def __init__(self, vm_name):
        """"""
        complete = self.just_exec("vboxmanage --nologo list vms")
        if vm_name not in [line.partition(" {")[0].strip('"') for line in complete.stdout.split("\n") if line]:
            raise Exception(f"No such VM {vm_name}")
        self.name = vm_name

    @classmethod
    def list(cls):
        """Returns list of VM names in VirtualBox"""
        command = "vboxmanage --nologo list vms"
        logging.debug(f"Executing {command}")
        complete = run(command,capture_output=True, shell=True, check=True, text=True)
        logging.debug(f"Output: {complete.stdout}")
        vm_list = [line.partition(" {")[0].strip('"') for line in complete.stdout.split("\n") if line]
        logging.info(f"Virtualbox machine guests are: {vm_list}")
        

    def just_exec(self, command):
        """Executes command"""
        logging.debug(f"Executing {command}")
        complete = run(command, shell=True, capture_output=True, check=True, text=True)
        #logging.debug(f"Output: {complete.stdout}")
        return complete

    def state(self):
        """Returns vm state string."""
        complete = self.just_exec(f'vboxmanage --nologo showvminfo "{self.name}"')
        match = re.search(r"^State:\s+(.+)$", complete.stdout, re.MULTILINE)
        if match:
            state_str = match.group(1)
            logging.info(f"Guest {self.name} is {state_str}")
            return state_str
    
    def is_running(self):
        """Returns True if vm is running, false otherwise"""
        if "powered off" in self.state():
            logging.info(f"Guest {self.name} is running: {False}")
            return False
        elif "running" in self.state():
            logging.info(f"Guest {self.name} is running: {True}")
            return True

    def start(self):
        logging.info(f"Starting up {self.name}")
        self.just_exec(f'vboxmanage --nologo startvm "{self.name}"')
        time.sleep(3)

    def poweroff(self):
        """Poweroff VM"""
        logging.info(f"Poweroff {self.name}")
        self.just_exec(f'vboxmanage --nologo controlvm "{self.name}" poweroff')
        time.sleep(2)

    def list_snapshots(self):
        """Returns list of image names"""
        complete = self.just_exec(f'vboxmanage --nologo snapshot "{self.name}" list --machinereadable')
        snapshot_list = [l.partition("=")[2].strip('"') for l in complete.stdout.split("\n") if l.startswith("SnapshotName")]
        logging.info(f"Guest {self.name} has these snapshots: {snapshot_list}")
        return snapshot_list

    def restore_snapshot(self, snapshot_name):
        """Returns list of image names"""
        logging.info(f"Restoring snapshot {snapshot_name}")
        complete = self.just_exec(f'vboxmanage --nologo snapshot "{self.name}" restore "{snapshot_name}"')
        #time.sleep(2)

    def create_snapshot(self, snapshot_name):
        """Creates snapshot"""
        logging.info(f"Taking snapshot {snapshot_name}")
        complete = self.just_exec(f'vboxmanage --nologo snapshot "{self.name}" take "{snapshot_name}"')
        #time.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s func=%(funcName)s %(levelname)s %(message)s", level=logging.info)
    print(VM.list())
    gw = VM("R80.20 GW")
    print(gw.list_snapshots())
    gw.start()
    if gw.is_running():
        gw.poweroff()
    if gw.is_running():
        gw.poweroff()
    print(gw.state())
    #gw.restore_snapshot("fresh_install2")
    #gw.start()





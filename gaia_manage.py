#!/usr/bin/env python

import logging
import json
import paramiko
import time
from random import random
import re
import argparse


class SG:
    first_time_config = {"hostname": "cpgw-x",
        "ftw_sic_key": "Nbdps!234",
        "install_security_managment": "false",
        "install_security_gw": "true",
        "gateway_daip": "false",
        "install_ppak": "true",
        "gateway_cluster_member": "false",
        "download_info": "true",
        "upload_info": "true",
        "domain_name":  "megafon-retail.ru",
        "primary": "8.8.8.8",
        "secondary": "4.4.4.4",
        "timezone": 'Europe/Moscow',
            }
    default_address = "192.168.1.1"
    default_login = "admin"
    default_password = "admin"
    default_expert_password = "Nbdps!234"

    def __init__(self, **kwargs):
        self.gateway_address = kwargs.get("gateway_address", SG.default_address)
        self.login = kwargs.get("login", SG.default_login)
        self.password = kwargs.get("password", SG.default_password)
        self.expert_password = kwargs.get("expert_password", SG.default_expert_password)
        self.first_time_config = SG.first_time_config.copy()
        self.ssh = None
        self.ssh_buffer = ""

    def set_first_time_config(self, **kwargs):
        """
        Takes keyword arguments and copies their values to first_time_config dictionary of
        instance if keyword is supported first time config value. first_time_config dict already contains default values after init.
        """
        for attr in [k for k in kwargs.keys() if k in SG.first_time_config]:
            self.first_time_config[attr] = kwargs[attr]
        
    def dump(self):
        logging.info("Gateway address: " + self.gateway_address)
        logging.info("First time configuration: \n" + json.dumps(self.first_time_config, indent=4))
        logging.info("\n")

    def start_ssh(self):
        self.ssh = paramiko.SSHClient()
        try:
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.gateway_address, username=self.login, password=self.password)
            self.channel = self.ssh.invoke_shell(height=1000)
            self.read_until(">")
            logging.info(f"SSH established with {self.gateway_address}")
        except paramiko.ssh_exception.SSHException as e:
            logging.error(f"SSH error with {self.gateway_address}: {e}")
            #self.ssh = None
            raise e

    def wait_ssh(self, timeout=60):
        """wait_ssh tries to establish ssh connection every 5 seconds. If connection established before timeout, instance ssh is setted as paramiko ssh client, exception is raised otherwise"""
        try_until_time = time.time() + timeout 
        ssh = None
        logging.info(f"Waiting {self.gateway_address} for {timeout} seconds..")

        while not ssh:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(self.gateway_address, username=self.login, password=self.password)
            except paramiko.ssh_exception.NoValidConnectionsError as e:
                if time.time() >= try_until_time:
                    logging.error("Timeout reached.")
                    raise e
                else:
                    ssh = None
                    time.sleep(5)
        self.ssh = ssh
        self.channel = self.ssh.invoke_shell(height=1000)
        self.read_until(">")
        logging.info(f"Connected with {self.gateway_address}")
        return ssh

    def close_ssh(self):
        if "close" in dir(self.ssh):
            logging.info(f"Closing connection with {self.gateway_address}")
            self.ssh.close()

    def read_until(self, *end_strings):
        buff = ""
        while not any([buff.strip().endswith(s) for s in end_strings]):
            resp = self.channel.recv(1024).decode("utf-8")
            buff += resp
            logging.debug(f"Read is 🎬{resp}🎬")
            logging.debug(f"Expectation string checks: {[(s, buff.strip().endswith(s)) for s in end_strings]}")
            logging.debug(f"Read cycle exit: {any([buff.strip().endswith(s) for s in end_strings])}")
            time.sleep(0.5)
            if not self.channel.get_transport().is_active():
                logging.info(f"SSH session is not active anymore")
                self.channel = None
                self.ssh = None
                break

        logging.debug("Read finished.")        
        self.ssh_buffer += buff
        return buff


    def send(self, string):
        logging.debug(f"Sending to SSH channel 🎬{string}🎬")
        self.channel.send(string)
        wait_some_time()
        logging.debug(f"Sending exec character")
        self.channel.send("\n")



    def set_expert_password(self, new_pwd, old_pwd=""):
        if not self.ssh:
            self.start_ssh()
        if not self.ssh:
            sys.exit(f"Can't establish SSH connection with {self.gateway_address}")
        
        logging.info(f"Changing expert password on {self.gateway_address}..")
        self.send("set expert-password")
        read = self.read_until(":", ">")
        if "Enter current expert password:" in read:
            self.send(old_pwd)
            read = self.read_until(":", ">")
            if "Wrong password" in read:
                raise Exception("Wrong current expert password.")
            elif "Enter new expert password:" in read:
                self.send(new_pwd)
                self.read_until("Enter new expert password (again):")
                self.send(new_pwd)
                self.read_until(">")
        elif "Enter new expert password:" in read:
            self.send(new_pwd)
            self.read_until("Enter new expert password (again):")
            self.send(new_pwd)
            self.read_until(">")
        elif "CLINFR0509" in read or "CLINFR0519" in read:
            self.send("lock database override")
            self.read_until(">")
            self.set_expert_password(new_pwd, old_pwd)
            return
        logging.info(f"Done changing expert password on {self.gateway_address}")
        
    def expert(self):
        """Enter expert mode"""
        if not self.ssh:
            self.start_ssh()
        if not self.ssh:
            sys.exit(f"Can't establish SSH connection with {self.gateway_address}")
        
        logging.info(f"Entering expert mode on {self.gateway_address}")
        if self.ssh_buffer.strip().endswith("#"):
            logging.info("Already expert")
            return
        elif self.ssh_buffer.strip().endswith(">"):
            self.send("expert")
            read = self.read_until("Enter expert password:", ">")
            if "Enter expert password:" in read:
                self.send(self.expert_password)
                read = self.read_until("#", ">")
                if "Wrong password" in read:
                    raise Exception("Wrong expert password.")
                return
            elif "Expert password has not been defined" in read:
                raise Exception("Expert password not set.")


    def clish(self):
        """Return from expert to clish"""
        if not self.ssh:
            self.start_ssh()
        if not self.ssh:
            sys.exit(f"Can't establish SSH connection with {self.gateway_address}")
        
        if self.ssh_buffer.strip().endswith(">"):
            return
        elif self.ssh_buffer.strip().endswith("#"):
            logging.info(f"Returning to CLIsh")
            #chr(4) = ctrl-d
            self.send(chr(4))
            self.read_until(">")
            return


    def get_password_hash(self, password):
        """Returns hash string matching password parameter. get_password_hash method creates new temp user, sets its password and reads its password-hash from config. Temp user is tnen deleted."""
        if not self.ssh:
            self.start_ssh()
        if not self.ssh:
            sys.exit(f"Can't establish SSH connection with {self.gateway_address}")

        self.clish()
        self.send("add user wrhhasderrrjqw uid 212 homedir /home/wrhhasderrrjqw")
        read = self.read_until(">")

        if "CLINFR0509" in read or "CLINFR0519" in read:
            self.send("lock database override")
            self.read_until(">")
            self.send("add user wrhhasderrrjqw uid 212 homedir /home/wrhhasderrrjqw")
            self.read_until(">")

        self.send("set user wrhhasderrrjqw password")
        self.read_until("New password:")
        self.send(password)
        self.read_until("Verify new password:")
        self.send(password)
        read = self.read_until(">")
        if "NMSUSR" in read or "CLINFR" in read:
            raise Exception(read)


        self.send("show configuration user")
        read = self.read_until(">")

        pwd_hash = ""
        match = re.search(r"set user wrhhasderrrjqw password-hash (.+)$", read,re.MULTILINE)
        if match:
            pwd_hash = match.group(1)
        else:
            raise Exception("Could not read password hash")
        logging.info(f"Hash for {password} is {pwd_hash}")

        self.send("delete user wrhhasderrrjqw")
        self.read_until(">")

        return pwd_hash


    def set_admin_password(self, password):
        """Sets passwords for user admin"""
        if not self.ssh:
            self.start_ssh()
        if not self.ssh:
            sys.exit(f"Can't establish SSH connection with {self.gateway_address}")

        self.clish()
        logging.info(f"Reseting admin password on {self.gateway_address}") 
        password_hash = self.get_password_hash(password)

        self.send("set user admin password")
        self.read_until("New password:")
        self.send(password)
        self.read_until("Verify new password:")
        self.send(password)
        read = self.read_until(">")
        if "NMSUSR" in read or "CLINFR" in read:
            raise Exception(read)

    def apply_ftc(self):
        """aply_ftc executes config_system -s "config_string" . config_string is build upon set_first_time_config method parameters. Gateway must be rebooted after ftc."""
        
        if not self.ssh:
            self.start_ssh()
        if not self.ssh:
            sys.exit(f"Can't establish SSH connection with {self.gateway_address}")
        config_string = "&".join([p + "=" + v for (p,v) in self.first_time_config.items()])
        logging.info(f"Applying first time config on {self.gateway_address}: {config_string}")
        self.expert()
        self.send(f'config_system -s "{config_string}"')
        self.read_until("First time configuration was completed!")
        self.close_ssh()


    def save(self):
        """Executes save config"""
        self.clish_execute("save config")

    def reboot(self):
        """Reboots gateway"""
        if not self.ssh:
            self.start_ssh()
        if not self.ssh:
            sys.exit(f"Can't establish SSH connection with {self.gateway_address}")
        
        logging.info(f"Rebooting {self.gateway_address}")
        self.clish()
        self.send("lock database override")
        self.read_until(">")

        self.send("reboot")
        read = self.read_until("Are you sure you want to reboot?(Y/N)[N]", "Do you want to save it now?(Y/N)[N]")
        if "Do you want to save it now?" in read:
            self.send("N")
            read = self.read_until("Are you sure you want to reboot?(Y/N)[N]")
            self.send("Y")
            self.read_until(">")
        elif "Are you sure you want to reboot?(Y/N)[N]" in read:
            self.send("Y")
            self.read_until(">")

        self.close_ssh()

    def set_interface(self, interface, **kwargs):
        """Executes set interface <interface> command. Additional keyword argument parameters must fit set interface clish command.
            Examples:
                set_interface("eth1", state="on")
                set_interface("eth1", ipv4-address="10.2.2.2", mask-length="24")
        """
        command = f"set interface {interface} {' '.join([k + ' ' + v for (k,v) in kwargs.items()])}"
        logging.info(f"Executing {command}")
        self.clish_execute(command)
        command = f"set interface {interface} state on"
        logging.info(f"Executing {command}")
        self.clish_execute(command)


    def clish_execute(self, command):
        """Executes command in clish"""
        self.clish()
        self.send("lock database override")
        self.read_until(">")
        logging.info(f"Executing {command}")
        self.send(command)
        read = self.read_until(">")
        logging.info(f"Reaction is {read}")
        match = re.search(r"^(CLI\w+|NMS\w+)\s+(.+)$", read, re.MULTILINE)
        if match:
            raise Exception(match.group(0))

    def get_configuration(self):
        """Returns current configuration"""
        self.clish()
        self.send("show configuration")
        read = self.read_until(">")
        return read

    def delete_ip(self, ip):
        """Deletes ip address."""
        pass

def wait_some_time():
    time.sleep(1+random())




def main():
    logfile_name = "gaia_manage.log"
    logging.basicConfig(format="%(asctime)s func=%(funcName)s %(levelname)s %(message)s", level=logging.INFO)
    logging.getLogger().addHandler(logging.FileHandler(logfile_name))

    parser = argparse.ArgumentParser(description='Setups Gaia with settings provided in config file.')
    parser.add_argument("config_json", help="JSON file with configuration")
    parser.add_argument("--address", help="Use this management address instead of default 192.168.0.1")
    args = parser.parse_args()
    config = {}
    with open(args.config_json) as f:
        config = json.load(f)

    logging.info(f"Started with config: {config}")
    address = "192.168.0.1" if not args.address else args.address
    gw = SG(gateway_address=address, login="admin", password=config["admin_password"])

    if "set_admin_password" in config:
        gw.set_admin_password(config["set_admin_password"])
        config["admin_password"] = config["set_admin_password"]
        gw.password = config["admin_password"]

    if "set_expert_password" in config:
        gw.set_expert_password(new_pwd=config["set_expert_password"])
        config["expert_password"] = config["set_expert_password"]
        gw.expert_password = config["expert_password"]
    
    if "interfaces" in config:
        logging.info("Setting up interfaces..")
        for i in config["interfaces"]:
            gw.set_interface(i["name"], **{k: v for k, v in i.items() if k != "name"})
        logging.info("Done")

    if "gateways" in config:
        logging.info("Processing default gateways..")
        for g in config["gateways"]:
            gw.clish_execute(f"set static-route default nexthop gateway address {g['gateway-address']} priority {g['priority']} on")
        logging.info("Done")

    gw.save()

    logging.info("Processing First time wizard..")
    gw.set_first_time_config(**config)
    gw.apply_ftc()
    logging.info("Done.")
    logging.info("Rebooting")
    gw.reboot()


if (__name__ == "__main__"): main()


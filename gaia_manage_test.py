#!/usr/bin/env python
import unittest
import time
from gaia_manage import SG
from vbox_control import VM
import logging

test_gw_addr = "10.0.101.241"
test_gw_login = "admin"
test_gw_pwd = ""
fresh_install = "fresh_install2"
vm = VM("R80.20 GW")
logging.basicConfig(format="%(asctime)s func=%(funcName)s %(levelname)s %(message)s", level=logging.DEBUG)


class SGTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass
    def test_SG0_init_default_params(self):
        self.assertEqual('foo'.upper(), 'FOO')
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())
        gw = SG()
        self.assertEqual(SG.first_time_config , gw.first_time_config)
        self.assertEqual(SG.default_address , gw.default_address)
        self.assertEqual(SG.default_login , gw.default_login)
        self.assertEqual(SG.default_password , gw.default_password)
        self.assertEqual(SG.default_expert_password , gw.expert_password)

    def test_SG0_init_params(self):
        ga = "10.0.0.1"
        lgn = "vasya"
        pwd = "123"
        xprt_pwd = "456"

        gw = SG(gateway_address=ga, login=lgn, password=pwd, expert_password=xprt_pwd)
        self.assertEqual(ga, gw.gateway_address)
        self.assertEqual(lgn, gw.login)
        self.assertEqual(pwd, gw.password)
        self.assertEqual(xprt_pwd, gw.expert_password)
        for k in gw.first_time_config:
            self.assertEqual(gw.first_time_config[k], SG.first_time_config[k])

    def test_SG0_set_first_time_config(self):
        gw = SG()
        ftc = {"hostname": "pentagon-x",
        "ftw_sic_key": "sickkkey",
        "domain_name":  "megafon-retail.ru",
        "primary": "8.8.8.8",
        "secondary": "4.4.4.4",
        "timezone": 'Europe/Moscow',
            }
        gw.set_first_time_config(**ftc)
        for k in ftc:
            self.assertEqual(ftc[k], gw.first_time_config[k])



    def test_SG11_ssh(self):
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()

        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd)
        gw.start_ssh()

        self.assertNotEqual(gw.ssh, None, "Something wrong when connecting to test gw with start_ssh()")
        
        gw.close_ssh()
        vm.poweroff()
        
    def test_SG12_read_until(self):
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd)
        gw.start_ssh()

        gw.send("show version all")
        buff = gw.read_until(">")

        self.assertTrue(buff.strip().endswith(">"))

        gw.close_ssh()
        vm.poweroff()


    def test_SG13_send(self):
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd)
        gw.start_ssh()

        gw.send("show version all")
        buff = gw.read_until(">")
        self.assertTrue("Product version" in buff and "OS build" in buff and "OS kernel" in buff, "Executing show version all and retrieving result went wrong.")

        gw.close_ssh()
        vm.poweroff()


    def test_SG13_set_expert_password(self):
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd)

        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()

        gw.start_ssh()
        #setting expert password for the first time, changing it two times, entering expert. Excepting # prompt
        gw.set_expert_password(new_pwd="dfgsdfgs12+")
        gw.set_expert_password(old_pwd="dfgsdfgs12+", new_pwd="dfgsdfgs11+")
        gw.set_expert_password(old_pwd="dfgsdfgs11+", new_pwd="dfgsdfgs12+")
        gw.expert_password = "dfgsdfgs12+"
        gw.expert()
        self.assertTrue(gw.ssh_buffer.strip().endswith("#"))
        gw.clish()
        #

        #Try changing expert with wrong current password. Excepting exception
        with self.assertRaises(Exception):
            gw.set_expert_password(old_pwd="dfgsdfgs11+sdfsfdsdfs", new_pwd="dfgsdfgs12+")
        #

        gw.close_ssh()
        vm.poweroff()

    def test_SG13_expert(self):
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()
        
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd)
        gw.start_ssh()
        
        #expert password is not set, expecting Exception
        with self.assertRaises(Exception):
            gw.expert()
        gw.close_ssh()
        #
        
        #trying with wrong expert password, expecting Exception
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd, expert_password="dfgsdfgs12+dssdfds")
        gw.set_expert_password(new_pwd="dfgsdfgs12+")
        gw.start_ssh()
        with self.assertRaises(Exception):
            gw.expert()
        #
        
        #trying with correct password, excepting # prompt
        gw.expert_password = "dfgsdfgs12+"
        gw.expert()
        self.assertTrue(gw.ssh_buffer.strip().endswith("#"))
        gw.close_ssh()

        vm.poweroff()

    def test_SG13_clish(self):
        
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()

        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd, expert_password="dfgsdfgs12+")
        gw.start_ssh()
        gw.set_expert_password(new_pwd="dfgsdfgs12+")

        #Trying enter clish when already in clish
        gw.clish()
        #

        #going to expert and then back to clish. > prompt excepted
        gw.expert()
        self.assertTrue(gw.ssh_buffer.strip().endswith("#"))
        gw.clish()
        self.assertTrue(gw.ssh_buffer.strip().endswith(">"))
        gw.close_ssh()

        vm.poweroff()
        

    def test14_get_password_hash(self):
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()
        
        #gettinh hash of new password, setting this hash to admin and trying to connect with new creds
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd, expert_password="dfgsdfgs12+")
        gw.start_ssh()

        hash1 = gw.get_password_hash("dfgsdfgs11+")

        gw.send("set user admin password-hash " + hash1)
        gw.read_until(">")

        gw.close_ssh()

        time.sleep(3)
        
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password="dfgsdfgs11+")
        gw.start_ssh()

        self.assertTrue(gw.ssh)
        #

        #check exception when passwords are short or simple
        with self.assertRaises(Exception):
            gw.get_password_hash("11111111")
        with self.assertRaises(Exception):
            gw.get_password_hash("qwe")
        #

        gw.close_ssh()
        vm.poweroff()


    def test15_set_admin_password(self):
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()
        
        #we'r setting admin password and trying to enter with new one
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd, expert_password="dfgsdfgs12+")
        gw.start_ssh()

        gw.set_admin_password("dfgsdfgs14+")
        gw.close_ssh()
        time.sleep(3)

        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password="dfgsdfgs14+")
        gw.start_ssh()
        self.assertTrue(gw.ssh)
        #

        gw.close_ssh()
        vm.poweroff()

    def test16_apply_ftc(self):
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()
        
        #
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd, expert_password="dfgsdfgs12+")
        ftc = {"hostname": "pentagon-x",
        "ftw_sic_key": "sickkkey",
        "domain_name":  "megafon-retail.ru",
        "primary": "8.8.8.8",
        "secondary": "4.4.4.4",
        "timezone": 'Europe/Moscow',
            }
        gw.set_first_time_config(**ftc)
        gw.start_ssh()

        gw.set_expert_password(new_pwd="dfgsdfgs12+")
        gw.apply_ftc()
        gw.start_ssh()
        gw.send("show configuration hostname")
        read = gw.read_until(">")
        self.assertTrue(ftc["hostname"] in read)
        #

        vm.poweroff()

    def test17_set_interface(self):
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()
        
        #
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd)
        with self.assertRaises(Exception):
            gw.set_interface("eth1", **{"ipv4-address": "10.2.2.ax2", "mask-length" : "24"})

        with self.assertRaises(Exception):
            gw.set_interface("eth1", **{"state": "fuckedup"})

        with self.assertRaises(Exception):
            gw.set_interface("ethrr1", **{"state": "on"})
        gw.set_interface("eth1", **{"ipv4-address": "10.2.2.2", "mask-length" : "24"})
        cfg = gw.get_configuration()
        self.assertTrue("set interface eth1 ipv4-address 10.2.2.2" in cfg)
        #
        gw.close_ssh()
        vm.poweroff()

    def test17_get_configuration(self):
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()
        
        #
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd)
        cfg = gw.get_configuration()
        self.assertTrue("set interface eth0" in cfg)
        self.assertTrue("set hostname" in cfg)
        #
        gw.close_ssh()
        vm.poweroff()

    def test18_wait_ssh(self):
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()
        
        #
        gw = SG(gateway_address="10.0.101.240", login=test_gw_login, password=test_gw_pwd)
        with self.assertRaises(Exception):
            gw.wait_ssh(10)
        #
        #
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd)
        gw.wait_ssh(10)
        self.assertTrue(gw.ssh)
        #
        vm.poweroff()
        


    def test20_mono(self):
        if vm.is_running():
            vm.poweroff()
        vm.restore_snapshot(fresh_install)
        vm.start()

        #
        gw = SG(gateway_address=test_gw_addr, login=test_gw_login, password=test_gw_pwd, expert_password="dfgsdfgs12+")
        config = gw.get_configuration()

        ftc = {"hostname": "pentagon-x",
        "ftw_sic_key": "sickkkey",
        "domain_name":  "megafon-retail.ru",
        "primary": "8.8.8.8",
        "secondary": "4.4.4.4",
        "timezone": 'Europe/Moscow',
            }
        gw.set_first_time_config(**ftc)
        gw.start_ssh()

        gw.set_expert_password(new_pwd="dfgsdfgs12+")
        gw.apply_ftc()
        gw.set_interface("eth1", **{"ipv4-address": "10.2.2.2", "mask-length" : "24"})
        gw.clish_execute("set static-route default nexthop gateway address 10.2.2.1 priority 1 on")
        gw.save()

        gw.reboot()
        time.sleep(15)
        gw.wait_ssh()
        cfg = gw.get_configuration()
        self.assertTrue("set interface eth1 ipv4-address 10.2.2.2" in cfg)
        self.assertTrue("set static-route default nexthop gateway address 10.2.2.1 priority 1 on" in cfg)
        
        #
        vm.poweroff()


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import ipaddress
import aiosnmp
import aioping
import telnetlib3
import configparser
import time
from aiosnmp.exceptions import SnmpTimeoutError
import platform
import logging
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


class TelnetSNMP:
    # Инициализация параметров для соединения 1
    def __init__(self, ip, login: str = 'admin', in_password: str = 'admin', commands: list = ""):
        self.username = login
        self.password = in_password
        self.ip = ip
        self.commands = commands

    # Получение назавние вендора/модель коммутатора по snmp
    async def snmp_vendor_id(self) -> tuple[str, str] | list[str]:
        try:
            # Получение данных по snmp
            async with aiosnmp.Snmp(host=self.ip, port=161, community='public', timeout=1) as snmp:
                results = await snmp.get('.1.3.6.1.2.1.1.1.0')
                result = ''
                print(self.ip)
                for res in results:
                    print(res.value)
                    result = res.value.decode("utf-8")
                # Распарсин по вендорам и вовзврат значения и ip устройсва
                if result.startswith('DES-3526') or result.strip().startswith('D-Link') or result.startswith(
                        'DXS') or result.startswith('DGS') or result.startswith(
                        'DES-1100-24') or result.startswith(
                        'DES-1100-16'):
                    if result.startswith('D-Link'):
                        vendor_id = result.split(' ')[1]
                        return vendor_id, self.ip
                    elif result.startswith('DXS'):
                        vendor_id = result.split(' ')[0]
                        return vendor_id, self.ip
                    elif result.startswith('DGS'):
                        vendor_id = result.split(' ')[0]
                        return vendor_id, self.ip
                    elif result.startswith('DES-3526'):
                        vendor_id = result.split(' ')[0]
                        return vendor_id, self.ip
                    elif result.startswith('DES-1100-16'):
                        vendor_id = result.split(' ')[0]
                        return vendor_id, self.ip
                    elif result.startswith('DES-1100-24'):
                        vendor_id = result.split(' ')[0]
                        return vendor_id, self.ip
                elif result.startswith('SNR') or result.startswith('QSW'):
                    vendor_id = result.split(',')[0].split(' ')[0]
                    return vendor_id, self.ip
                elif result.startswith('Edge-Core'):
                    # edge-core es3528m
                    vendor_id = result.split(' ')[4]
                    return vendor_id, self.ip
                elif result.startswith('Layer2+'):
                    # edge-core es3526xa
                    vendor_id = result.split(' ')[5]
                    return vendor_id, self.ip
                elif result.startswith('OmniStack'):
                    # alcotel
                    vendor_id = 'LS' + str(result.split(' ')[2])
                    return vendor_id, self.ip
                elif result.startswith('ES-2024A'):
                    # zyxel
                    vendor_id = result.split(' ')[0]
                    return vendor_id, self.ip
                elif result.startswith('S2326TP-EI') or result.startswith('S2352P-EI'):
                    vendor_id = result.split(' ')[0]
                    return vendor_id, self.ip
        except SnmpTimeoutError:
            print(f'Snmpwalk connect timeout to ip address: {self.ip}... ')
            return ['Connect timeout snmp ', self.ip]

    # Передаче комманд на выполнение в свитч
    async def shell(self, reader, writer) -> None:
        try:
            outp = await reader.read(1024)
            if outp is not None:
                print(
                    f'Connection is established to the ip address: {self.ip}...')

                writer.write(self.username + '\n')
                await asyncio.sleep(0.5)
                writer.write(self.password + '\n')
                await asyncio.sleep(0.5)
                for command in self.commands:
                    writer.write(command)
                    await asyncio.sleep(1)
                await asyncio.sleep(0.5)
                print(await reader.read(1024))
        except ConnectionResetError:
            print(f'Connection reset by peer: {self.ip}...')

    # Настройки и подвключение по telnet
    async def cli_connect(self) -> None:
        print(f'Connections to ip address: {self.ip}...')
        reader, writer = await telnetlib3.open_connection(self.ip, 23, connect_minwait=1.5, connect_maxwait=2,
                                                          shell=self.shell)
        await writer.protocol.waiter_closed

    async def wait_host_port(self, duration: int = 10, delay: int = 2) -> str | bool:
        tmax = time.time() + duration
        while time.time() < tmax:
            try:
                reader, writer = await asyncio.wait_for(asyncio.open_connection(self.ip, 22), timeout=5)
                writer.close()
                await writer.wait_closed()
                await asyncio.sleep(1)
                return
            except:
                if delay:
                    await asyncio.sleep(delay)
        return self.ip


def config() -> (str, str, str):
    conf_file = "config.ini"
    conf = configparser.ConfigParser()
    conf.read(conf_file)
    username = conf.get('default', 'username')
    password = conf.get('default', 'password')
    subnet = conf.get('default', 'subnet')
    return username, password, subnet


async def do_ping(host: str) -> str | None:
    try:
        delay = await aioping.ping(host, timeout=20) * 100
        print("Ping response in %s ms to ip " % round(delay, 2), host)
        await asyncio.sleep(1)
        return host
    except TimeoutError:
        # print("Timed out")
        return


async def pingTask(subnet: ipaddress.ip_network) -> list:
    tasks = []
    try:
        net = [str(ip) for ip in ipaddress.ip_network(subnet)]
    except ValueError:
        print('does not appear to be an IPv4 or IPv6 network')
        net = ['0.0.0.0']
    await asyncio.sleep(1)
    for ip in net:
        tasks.append(asyncio.create_task(do_ping(ip)))
    result = await asyncio.gather(*tasks)
    return result


async def main() -> None:
    username, password, subnet = config()
    switch_id: dict[str, list[str]] = {'DLINK': ['DES-3200-26', 'DES-3026', 'DES-3052', 'DES-1228', 'DXS-3326GSR', 'DES-3028', 'DES-1228/ME',
                                                 'DES-3526'],
                                       'SNR': ['QSW-2800-28T-M-AC', 'SNR-S2940-8G-v2', 'SNR-S2950-24G', 'SNR-S2960-24G', 'SNR-S2960-48G',
                                               'QSW-2800-28T-AC', 'QSW-2800-10T-AC', 'SNR-S2985G-48T', 'SNR-S2985G-8T', 'SNR-S2965-24T', 'SNR-S2985G-24TC', 'SNR-S2965-8T'],
                                       'EDGE': ['ES3528M', 'ES3526XA', 'ECS3510-28T', 'ES3528MV2'],
                                       'HUAWEI': ['S2352P-EI', 'S2326TP-EI'],
                                       'ALCATEL': ['LS6200']}
    commands: dict[str, list[str]] = {'DLINK': ['enable ssh\n',
                                                'config ssh authmode password enable\n',
                                                'config ssh server maxsession 3 contimeout 600 authfail 10 rekey '
                                                'never\n',
                                                'config ssh user admin authmode password\n',
                                                'config ssh algorithm RSA enable\n',
                                                'save\n'],
                                      'EDGE': ['config\n',
                                               'ip ssh server-key  size 512\n',
                                               'end\n',
                                               'ip ssh crypto host-key generate\n',
                                               'ip ssh save host-key\n',
                                               'config\n',
                                               'ip ssh server\n',
                                               'end\n',
                                               'copy running-config startup-config\n\n'],
                                      'SNR': ['config\n',
                                              'ssh-server enable\n',
                                              'end\n',
                                              'write\n',
                                              'Y\n'],
                                      'HUAWEI': ['system-view\n',
                                                 'aaa\n',
                                                 'local-user admin service-type ssh telnet terminal\n',
                                                 'q\n',
                                                 'stelnet server enable\n',
                                                 'ssh authentication-type default password\n',
                                                 'rsa local-key-pair create\n', 'y\n', '512\n',
                                                 'ssh user admin\n',
                                                 'ssh user admin authentication-type password\n',
                                                 'ssh user admin service-type all\n',
                                                 'user-interface vty 0 4\n',
                                                 'authentication-mode aaa\n',
                                                 'user privilege level 15\n',
                                                 'idle-timeout 30 0\n',
                                                 'protocol inbound all\n'
                                                 'q\n', 'q\n', 'save\n', 'y\n'],
                                      'ALCATEL': ['dir',
                                                  'configure\n',
                                                  'crypto key generate dsa\n',
                                                  'y\n',
                                                  'ip ssh server\n',
                                                  'end\n',
                                                  'copy running-config startup-config\n',
                                                  'y\n']}
    # Получаем маску сети и если она меньше 24-бит, то делим сеть на 24-бита
    mask = str(ipaddress.ip_network(subnet).netmask).split('.')
    subnet = ipaddress.ip_network(subnet)
    maskbit = 0
    for i in mask:
        res = int(bin(int(i))[2:].count('1'))
        maskbit += res

    # Проверяем на доступност хостов и получаеш список доступных хостов
    pingTaskList = []
    if maskbit < 24:
        n = 24 - maskbit
        subnet = list(subnet.subnets(prefixlen_diff=n))
        for ipNet in subnet:
            pingTaskList.append(await pingTask(ipNet))
    else:
        pingTaskList = await pingTask(subnet)

    # Проверяем на открытость 22 порта на хостах и получаем список не доступных по 22 порту хостов
    tasksWaitHostPort = []
    if maskbit < 24:
        for net in pingTaskList:
            time.sleep(5)
            for ip in net:
                if isinstance(ip, str):
                    tasksWaitHostPort.append(asyncio.create_task(
                        TelnetSNMP(ip).wait_host_port()))
    else:
        for ip in pingTaskList:
            if isinstance(ip, str):
                tasksWaitHostPort.append(asyncio.create_task(
                    TelnetSNMP(ip).wait_host_port()))

    NoConnSsh = await asyncio.gather(*tasksWaitHostPort)
    
    # Получаем вендор id
    tasksVendorId = []
    for ip in NoConnSsh:
        if isinstance(ip, str):
            tasksVendorId.append(asyncio.create_task(
                TelnetSNMP(ip).snmp_vendor_id()))
    vendorId = await asyncio.gather(*tasksVendorId)
    # print(vendorId)
    tasksTelnet = []
    for task in vendorId:
        if task is not None:
            print(task)

            if task[0] in switch_id.get('DLINK'):
                ip = task[1]
                command = commands.get('DLINK')
                tasksTelnet.append(asyncio.create_task(
                    TelnetSNMP(ip, username, password, command).cli_connect()))

            elif task[0] in switch_id.get('EDGE'):
                ip = task[1]
                command = commands.get('EDGE')
                tasksTelnet.append(asyncio.create_task(
                    TelnetSNMP(ip, username, password, command).cli_connect()))

            elif task[0] in switch_id.get('SNR'):
                ip = task[1]
                command = commands.get('SNR')
                tasksTelnet.append(asyncio.create_task(
                    TelnetSNMP(ip, username, password, command).cli_connect()))

            elif task[0] in switch_id.get('HUAWEI'):
                ip = task[1]
                command = commands.get('HUAWEI')
                tasksTelnet.append(asyncio.create_task(
                    TelnetSNMP(ip, username, password, command).cli_connect()))
            elif task[0] in switch_id.get('ALCATEL'):
                ip = task[1]
                # cmdDir= commands.get('ALCATEL')[0]
                # print(cmdDir)
                
                command = commands.get('ALCATEL')
                tasksTelnet.append(asyncio.create_task(
                     TelnetSNMP(ip, username, password, command).cli_connect()))

    await asyncio.gather(*tasksTelnet)

if __name__ == '__main__':
    asyncio.run(main())

import asyncio
import ipaddress

import aiosnmp
import telnetlib3
from aiosnmp.exceptions import SnmpTimeoutError


class TelnetSNMP:
    # Инициализация параметров для соединения 
    def __init__(self, ip, login: str = 'admin', in_password: str = 'admin', commands: list = ""):
        self.username = login
        self.password = in_password
        self.ip = str(ip)
        self.commands = commands

    # Получение назавние вендора/модель коммутатора по snmp
    async def snmp_vendor_id(self) -> tuple[str, str] | list[str]:
        try:
            # Получение данных по snmp
            async with aiosnmp.Snmp(host=self.ip, port=161, community='public', timeout=1) as snmp:
                results = await snmp.get('.1.3.6.1.2.1.1.1.0')
                result = ''
                for res in results:
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
        except SnmpTimeoutError:
            print(f'Snmpwalk connect timeout to ip address: {self.ip}... ')
            return ['Connect timeout snmp ', self.ip]

    # Передаче комманд на выполнение в свитч
    async def shell(self, reader, writer) -> None:
        try:
            outp = await reader.read(1024)
            if outp is not None:
                print(f'Connection is established to the ip address: {self.ip}...')
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


async def main(uname: str, pwd: str, snet: str) -> None:
    tasks = []
    tasks_telnet = []
    vendor_id = []
    switch_id = {'DLINK': ['DES-3200-26', 'DES-3026', 'DES-3052', 'DES-1228', 'DXS-3326GSR', 'DES-3028', 'DES-1228/ME',
                           'DES-3526', 'DES-1100-16', 'DES-1100-24'],
                 'SNR': ['QSW-2800-28T-M-AC', 'SNR-S2940-8G-v2', 'SNR-S2950-24G', 'SNR-S2960-24G', 'SNR-S2960-48G',
                         'QSW-2800-28T-AC', 'QSW-2800-10T-AC', 'SNR-S2985G-48T', 'SNR-S2985G-8T'],
                 'EDGE': ['ES3528M', 'ES3526XA', 'ECS3510-28T', 'ES3528MV2'], }
    commands: dict[str, list[str]] = {'DLINK': ['enable ssh\n',
                                                'config ssh authmode password enable\n',
                                                'config ssh server maxsession 3 contimeout 600 authfail 10 rekey '
                                                'never\n',
                                                'config ssh user admin authmode password\n',
                                                'config ssh algorithm RSA enable\n',
                                                'save\n'],
                                      'EDGE': ['ip ssh crypto host-key generate\n',
                                               'ip ssh save host-key\n',
                                               'config\n',
                                               'ip ssh server\n',
                                               'end\n',
                                               'copy running-config startup-config\n\n'],
                                      'SNR': ['config\n',
                                              'ssh-server enable\n',
                                              'end\n',
                                              'write\nY\n']}
    try:
        net = [str(ip) for ip in ipaddress.ip_network(snet)]
    except ValueError:
        print('does not appear to be an IPv4 or IPv6 network')
        net = ['0.0.0.0']

    for ip in net:
        if ip != '0.0.0.0':
            tasks.append(asyncio.create_task(TelnetSNMP(ip).snmp_vendor_id()))

    for task in tasks:
        vendor_id.append(await task)

    for t in vendor_id:
        if t is not None:
            if t[0] in switch_id.get('DLINK'):
                ip = t[1]
                command = commands.get('DLINK')
                tasks_telnet.append(asyncio.create_task(
                    TelnetSNMP(ip, uname, pwd, command).cli_connect()))

            elif t[0] in switch_id.get('EDGE'):
                ip = t[1]
                command = commands.get('EDGE')
                tasks_telnet.append(asyncio.create_task(
                    TelnetSNMP(ip, uname, pwd, command).cli_connect()))

            elif t[0] in switch_id.get('SNR'):
                ip = t[1]
                command = commands.get('SNR')
                tasks_telnet.append(asyncio.create_task(
                    TelnetSNMP(ip, uname, pwd, command).cli_connect()))

    for task in tasks_telnet:
        await task


username = input('login: ')
password = input('password: ')
subnet = input('Enter to subnet: ')
asyncio.run(main(username, password, subnet))

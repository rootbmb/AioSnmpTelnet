import asyncio
import aioping
import ipaddress
import time

async def do_ping(host):
    try:
        delay = await aioping.ping(host,timeout=100) * 1000
        print("Ping response in %s ms" % delay)
        await asyncio.sleep(2)

    except TimeoutError:
        print("Timed out")
        return host

async def ping_task(subnet):
            tasks=[]
            print(subnet)
            try:
                net = [str(ip) for ip in ipaddress.ip_network(subnet)]
            except ValueError:
                print('does not appear to be an IPv4 or IPv6 network')
                net = ['0.0.0.0']
            time.sleep(5)
            for ip in net:
                print(ip)
                tasks.append(asyncio.create_task(do_ping(ip)))
            result = await asyncio.gather(*tasks)
            print(result)

async def main():
    subnet = '10.10.4.0/22'
    mask = str(ipaddress.ip_network(subnet).netmask).split('.')
    subnet = ipaddress.ip_network(subnet)
    bit = 0
    for i in mask:    
        res = int(bin(int(i))[2:].count('1'))
        bit += res
    
    tasks = []

    if bit < 24:
        n = 24 - bit
        subnet = list(subnet.subnets(prefixlen_diff=n))
        print(subnet)
        for ipNet in subnet:
            await ping_task(ipNet)
    else:
        await ping_task(subnet)
         

asyncio.run(main())

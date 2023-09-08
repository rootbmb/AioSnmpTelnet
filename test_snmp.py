import asyncio
import aiosnmp

async def main():
    async with aiosnmp.Snmp(host="10.10.6.17", port=161, community="public") as snmp:
        for res in await snmp.get(".1.3.6.1.2.1.1.1.0"):
            print(res.oid, res.value)

asyncio.run(main())
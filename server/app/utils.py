"""Utility functions for the server application."""
import random
import socket
import string


def getLocalIPs() -> list[str]:
    """Retrieve all local IP addresses (IPv4 and IPv6, including link-local) using both hostname lookup and socket connections."""
    ips = set()

    # Method 1: Hostname lookup
    try:
        hostName = socket.gethostname()
        # IPv4
        ips.update(socket.gethostbyname_ex(hostName)[2])
    except Exception as e:
        print(f'Error retrieving IPv4 addresses: {e}')
    try:
        # IPv6
        addrInfos = socket.getaddrinfo(hostName, None, socket.AF_INET6)
        for info in addrInfos:
            ips.add(info[4][0])
    except Exception as e:
        print(f'Error retrieving IPv6 addresses: {e}')

    # Method 2: Dummy socket connections
    try:
        # IPv4
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            ips.add(s.getsockname()[0])
    except Exception as e:
        print(f'Error retrieving external IPv4 address: {e}')
    try:
        # IPv6
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as s:
            s.connect(('2001:4860:4860::8888', 80))
            ips.add(s.getsockname()[0])
    except Exception as e:
        print(f'Error retrieving external IPv6 address: {e}')

    return list(ips)

def isHostIP(ip: str | None) -> bool:
    """Check if the given IP is a local IP address."""
    if (ip == '127.0.0.1'):
        return True
    return (ip is not None and ip in getLocalIPs())


def generateRandomString(length: int) -> str:
    """Generate a random string of letters and digits with a given length"""
    return ''.join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )

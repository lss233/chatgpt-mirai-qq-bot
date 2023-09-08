import socket


def is_open(ip, port):
    """Check if a host and port is open"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        # True if open, False if not
        is_port_open = sock.connect_ex((ip, int(port))) == 0
        if is_port_open:
            sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        is_port_open = False
    sock.close()
    return is_port_open

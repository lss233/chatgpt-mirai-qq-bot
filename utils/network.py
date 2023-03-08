import socket


def is_open(ip, port):
    """Check if a host and port is open"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        # True if open, False if not
        is_open = s.connect_ex((ip, int(port))) == 0
        if is_open:
            s.shutdown(socket.SHUT_RDWR)
    except Exception:
        is_open = False
    s.close()
    return is_open

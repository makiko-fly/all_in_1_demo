import socket
import time

def is_service_reachable(host, port, timeout=1):
    """Test if a host:port is reachable"""
    try:
        socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_obj.settimeout(timeout)
        result = socket_obj.connect_ex((host, port))
        socket_obj.close()
        return result == 0
    except socket.error:
        return False
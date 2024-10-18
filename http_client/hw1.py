"""
HTTP client 1.0
"""
import socket
import sys
import ssl
from urllib.parse import urlparse


def retrieve_url(url):
    """
    return bytes of the body of the document at url
    """
    try:
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        path = parsed_url.path if parsed_url.path else "/"
        port = (
            parsed_url.port if parsed_url.port
            else (443 if parsed_url.scheme == 'https' else 80)
            )
        timeout = 10  # Set the timeout duration in seconds

        # Construct header
        message = f"GET {path} HTTP/1.1\r\n".encode()
        message += f"Host: {host}:{port}\r\n".encode()
        message += b"Connection: close\r\n"
        message += b"\r\n"

        # Start a socket connection
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            try:
                # Handle https
                if parsed_url.scheme == 'https':
                    context = ssl.create_default_context()
                    s = context.wrap_socket(s, server_hostname=host)

                s.connect((host, port))
                print(f"Connected to {host}:{port}")
            except socket.timeout as e:
                print(f"Error: Timeout when connecting to {host}:{port} - {e}")
                return None
            except socket.gaierror as e:
                print(f"Error: DNS failed for {host}:{port} - {e}")
                return None
            except ssl.SSLError as e:
                print(f"Error: SSL error - {e}")
                return None

            # Send an HTTP GET request
            s.sendall(message)
            # Receive the response
            res = b''
            while True:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    res += chunk
                except socket.timeout:
                    print("Error: Timeout while receiving data")
                    return None
            header, body = res.split(b"\r\n\r\n", 1)
            if (b"301 Moved Permanently" in header or
                    b"302 Found" in header):  # handle redirect
                return None
            if b'Transfer-Encoding: chunked' in header:  # handle chunked data
                decoded_body = b''
                while True:
                    index = body.find(b'\r\n')
                    if index == -1:
                        break
                    length = int(body[:index].decode(), 16)
                    if length == 0:
                        break
                    start = index + 2
                    end = start + length
                    decoded_body += body[start:end]
                    body = body[end+2:]
                return decoded_body
            if b'200 OK' in header:  # only return body when 200 OK
                return body
            else:
                return None
    except socket.timeout:
        print("Error: Timeout while receiving data")
        return None
    except ssl.SSLError as e:
        print(f"Error: SSL error - {e}")
        return None


if __name__ == "__main__":
    result = retrieve_url(sys.argv[1])
    if result:
        sys.stdout.buffer.write(result)  # pylint: disable=no-member
    else:
        print("Fail to retrieve the URL")

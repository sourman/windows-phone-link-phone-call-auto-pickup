import socket, os, sys
result_file = os.path.join(os.path.dirname(__file__), 'dns-test-result.txt')
with open(result_file, 'w') as f:
    f.write('CWD: ' + os.getcwd() + '\n')
    f.write('PATH: ' + os.environ.get('PATH', '') + '\n')
    try:
        ips = socket.getaddrinfo('api.telegram.org', 443)
        f.write('DNS OK: ' + str(ips[:2]) + '\n')
    except Exception as e:
        f.write('DNS FAILED: ' + str(e) + '\n')
    f.write('Python: ' + sys.executable + '\n')
    f.write('Version: ' + sys.version + '\n')

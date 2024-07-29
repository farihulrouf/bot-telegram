import paramiko

# Setup SSH client
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Load private key
private_key_path = '/home/farihul/.ssh/id_rsa'
private_key = paramiko.RSAKey.from_private_key_file(private_key_path)

# Connect to the server
try:
    ssh.connect('128.199.76.91', username='peratan', pkey=private_key)
    print("Connected successfully.")
    # Perform operations
finally:
    ssh.close()

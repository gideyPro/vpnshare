#!/bin/bash

# Check if openssh is installed
if ! command -v sshd &> /dev/null; then
    echo "openssh is not installed. Please install it by running 'pkg install openssh'."
    exit 1
fi

# Start the SSH server
sshd

# Get the username
USER=$(whoami)

# Get the IP address
IP=$(ip addr show | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | cut -d/ -f1)

# Get the port
PORT=8022

echo "SSH server started."
echo "On your Linux PC, use the following details to connect:"
echo "Username: $USER"
echo "IP Address: $IP"
echo "Port: $PORT"

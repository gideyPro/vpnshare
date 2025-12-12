#!/bin/bash

# Check if openssh is installed
if ! command -v sshd &> /dev/null; then
    echo "openssh is not installed. Please install it by running 'pkg install openssh'."
    exit 1
fi

# --- SSH Server Configuration ---
SSHD_CONFIG=$PREFIX/etc/ssh/sshd_config

# Check if AllowTcpForwarding is enabled, if not, enable it
if ! grep -q "^AllowTcpForwarding yes" "$SSHD_CONFIG"; then
    echo "Enabling AllowTcpForwarding in sshd_config..."
    # Remove any existing AllowTcpForwarding line
    sed -i '/^AllowTcpForwarding/d' "$SSHD_CONFIG"
    # Add the required setting
    echo "AllowTcpForwarding yes" >> "$SSHD_CONFIG"
    # Restart the SSH server to apply changes
    pkill sshd || true
    echo "Restarting sshd..."
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

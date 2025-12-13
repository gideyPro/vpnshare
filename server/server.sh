#!/bin/bash

# Function to print error and exit
die() { echo "Error: $1" >&2; exit 1; }

# Check if openssh is installed
if ! command -v sshd &> /dev/null; then
    echo "openssh is not installed. Installing..."
    pkg update && pkg install openssh -y || die "Failed to install openssh. Please install it manually with 'pkg install openssh'."
fi

# Check if sshd is already running
if pgrep sshd >/dev/null; then
    echo "SSH server is already running."
else
    echo "Starting SSH server..."
    sshd || die "Failed to start sshd"
fi

<<<<<<< HEAD
# Ensure authentication logic is clear
if [ ! -f "$HOME/.ssh/authorized_keys" ]; then
    echo "----------------------------------------------------------------"
    echo "WARNING: No SSH keys found."
    echo "To connect, you must either:"
    echo "1. Set a password by running the command: passwd"
    echo "2. Copy your public key to ~/.ssh/authorized_keys"
    echo "----------------------------------------------------------------"
fi
=======
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
>>>>>>> 7a71f7966be2f739f7d0c5195de6d98fccf7a8a1

# Get the username
USER=$(whoami)

# Get the port (Default Termux SSH port)
PORT=8022

echo ""
echo "SSH Server Started Successfully"
echo "----------------------------------------------------------------"
echo "Connection Details for Linux Client:"
echo "Username : $USER"
echo "Port     : $PORT"
echo "IP Addresses:"

# List all non-local IPv4 addresses
found_ip=0
for ip in $(ip -4 addr show | grep inet | grep -v '127.0.0.1' | awk '{print $2}' | cut -d/ -f1); do
    echo " - $ip"
    found_ip=1
done

if [ "$found_ip" -eq 0 ]; then
    echo " - No active network IP found (besides localhost)."
    echo "   Ensure you are connected to Wi-Fi or have a valid network interface."
fi
echo "----------------------------------------------------------------"

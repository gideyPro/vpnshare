#!/bin/bash
set -e

# Configuration
SSH_PORT=8022

# Check if sshuttle is installed
if ! command -v sshuttle &> /dev/null; then
    echo "Error: sshuttle is not installed."
    echo "Please install it with: sudo apt install sshuttle"
    exit 1
fi

echo "=========================================="
echo "      Android VPN Tethering (sshuttle)    "
echo "=========================================="

# Get Connection Details
read -p "Enter Android Device IP: " ANDROID_IP
if [ -z "$ANDROID_IP" ]; then
    echo "Error: IP address is required."
    exit 1
fi

read -p "Enter Android Username (e.g. u0_a123): " ANDROID_USER
if [ -z "$ANDROID_USER" ]; then
    echo "Error: Username is required."
    exit 1
fi

echo ""
echo "Starting VPN sharing..."
echo "Connecting to $ANDROID_USER@$ANDROID_IP:$SSH_PORT"
echo "Traffic and DNS will be routed through the Android device."
echo "Press Ctrl+C to stop."
echo "------------------------------------------"

# Run sshuttle
# --dns: Forward DNS queries
# -r: Remote server (user@host:port)
# 0.0.0.0/0: Route all traffic
# -x: Exclude the remote server IP to prevent routing loops
sshuttle --dns -r "$ANDROID_USER@$ANDROID_IP:$SSH_PORT" 0.0.0.0/0 -x "$ANDROID_IP"

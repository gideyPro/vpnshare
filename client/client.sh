#!/bin/bash
set -e

# --- Configuration ---
SSH_PORT=8022
SOCKS_PORT=9050
REDSOCKS_PORT=12345
DNS_PORT=5353
# Public DNS server to forward queries to
DNS_SERVER="8.8.8.8"

# --- Process IDs ---
SSH_PID=
REDSOCKS_PID=
SOCAT_PID=

# --- Cleanup Function ---
cleanup() {
    echo "Closing connection and cleaning up..."

    # Kill processes
    [ ! -z "$SSH_PID" ] && kill $SSH_PID 2>/dev/null
    [ ! -z "$REDSOCKS_PID" ] && kill $REDSOCKS_PID 2>/dev/null
    [ ! -z "$SOCAT_PID" ] && kill $SOCAT_PID 2>/dev/null

    # Restore iptables rules
    # The order is the reverse of the order they were added.
    iptables -t nat -D PREROUTING -p udp --dport 53 -j REDIRECT --to-port $DNS_PORT 2>/dev/null || true
    iptables -t nat -D OUTPUT -p udp --dport 53 -j REDIRECT --to-port $DNS_PORT 2>/dev/null || true
    iptables -t nat -D PREROUTING -p tcp -j REDSOCKS 2>/dev/null || true
    iptables -t nat -D OUTPUT -p tcp -j REDSOCKS 2>/dev/null || true
    iptables -t nat -F REDSOCKS 2>/dev/null || true
    iptables -t nat -X REDSOCKS 2>/dev/null || true

    # Restore DNS settings
    if [ -f /etc/resolv.conf.bak ]; then
        mv /etc/resolv.conf.bak /etc/resolv.conf
    fi

    echo "Cleanup complete."
    exit 0
}

trap cleanup INT TERM EXIT

# --- Pre-flight Checks ---
# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Check for dependencies
for cmd in ssh redsocks socat nc; do
    if ! command -v $cmd &> /dev/null; then
        echo "$cmd could not be found. Please install it."
        exit 1
    fi
done

# --- Script Directory for Config File ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
REDSOCKS_CONFIG="$SCRIPT_DIR/redsocks.conf"
if [ ! -f "$REDSOCKS_CONFIG" ]; then
    echo "Configuration file not found: $REDSOCKS_CONFIG"
    exit 1
fi

# --- User Input ---
read -p "Enter Android device IP address: " ANDROID_IP
read -p "Enter Android device username: " ANDROID_USER

# --- Start Services ---
# 1. Start SSH tunnel
echo "Starting SSH tunnel..."
ssh -N -D $SOCKS_PORT -p $SSH_PORT "$ANDROID_USER@$ANDROID_IP" &
SSH_PID=$!

# Wait for the tunnel with a timeout
echo "Waiting for SOCKS proxy on port $SOCKS_PORT..."
for i in {1..10}; do
    if nc -z 127.0.0.1 $SOCKS_PORT; then
        echo "SOCKS proxy is active."
        break
    fi
    sleep 1
    if [ $i -eq 10 ]; then
        echo "Error: SOCKS proxy failed to start. Exiting."
        exit 1
    fi
done

# 2. Start redsocks for TCP traffic
echo "Starting redsocks..."
redsocks -c "$REDSOCKS_CONFIG" &
REDSOCKS_PID=$!

# 3. Start socat for DNS (UDP) traffic
echo "Starting socat for DNS..."
socat UDP-LISTEN:$DNS_PORT,fork SOCKS5:127.0.0.1:$DNS_SERVER:53,socksport=$SOCKS_PORT &
SOCAT_PID=$!
sleep 1 # Give socat a moment to start

# --- Configure Networking ---
echo "Configuring iptables and DNS..."

# 1. Backup and set new DNS
cp /etc/resolv.conf /etc/resolv.conf.bak
echo "nameserver 127.0.0.1" > /etc/resolv.conf

# 2. Configure iptables
# Create a new chain for our rules
iptables -t nat -N REDSOCKS

# Bypass LAN and other reserved addresses
iptables -t nat -A REDSOCKS -d 0.0.0.0/8 -j RETURN
iptables -t nat -A REDSOCKS -d 10.0.0.0/8 -j RETURN
iptables -t nat -A REDSOCKS -d 127.0.0.0/8 -j RETURN
iptables -t nat -A REDSOCKS -d 169.254.0.0/16 -j RETURN
iptables -t nat -A REDSOCKS -d 172.16.0.0/12 -j RETURN
iptables -t nat -A REDSOCKS -d 192.168.0.0/16 -j RETURN
iptables -t nat -A REDSOCKS -d 224.0.0.0/4 -j RETURN
iptables -t nat -A REDSOCKS -d 240.0.0.0/4 -j RETURN

# Redirect all other TCP traffic to the redsocks listener
iptables -t nat -A REDSOCKS -p tcp -j REDIRECT --to-ports $REDSOCKS_PORT

# Apply the REDSOCKS chain to outgoing and forwarded traffic
iptables -t nat -A OUTPUT -p tcp -j REDSOCKS
iptables -t nat -A PREROUTING -p tcp -j REDSOCKS

# Redirect DNS traffic (UDP port 53) to the socat listener
iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-port $DNS_PORT
iptables -t nat -A PREROUTING -p udp --dport 53 -j REDIRECT --to-port $DNS_PORT

# --- Main Loop ---
echo "✅ Connection established. All TCP and DNS traffic is now being routed through the Android device."
echo "Press Ctrl+C to disconnect."

# Wait for the SSH process to end
wait $SSH_PID

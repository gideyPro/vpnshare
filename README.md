# Android VPN Tethering for Linux

This project allows you to share your Android device's VPN connection with a Linux PC without requiring root access on the Android device. It uses Termux on the Android device to create an SSH server, and a script on the Linux PC to route all traffic through the Android device.

## Features

* Share VPN connection from an unrooted Android device.
* System-wide VPN connection on the Linux PC for both TCP and UDP traffic.
* No root access required on the Android device.

## Prerequisites

* **Android Device:**
    * Termux app installed.
    * An active VPN connection.
* **Linux PC:**
    * `ssh` client installed.
    * `redsocks` installed.
    * `socat` installed.
    * `ip` command available.

## How it works

The system works by creating an SSH tunnel from the Linux PC to the Android device, which establishes a SOCKS proxy. The `redsocks` service is then used to intercept all system-wide TCP traffic and forward it through the SOCKS proxy. For UDP traffic, specifically DNS, `socat` is used to create a DNS forwarder that sends queries through the SOCKS proxy. The Termux script on the Android device then forwards this traffic through the VPN connection.

## Setup

### Android (Server) Side

1. **Install Termux:** Install the Termux app from the Google Play Store or F-Droid.
2. **Install necessary packages:** Open Termux and run the following commands:
   ```bash
   pkg update
   pkg install openssh
   ```
3. **Set up SSH key-based authentication:**
   - On your **Linux PC**, generate an SSH key if you don't have one:
     ```bash
     ssh-keygen -t rsa -b 4096
     ```
   - Copy the public key to your Android device. A simple way is to use a temporary web server:
     - On your **Linux PC**, navigate to your `.ssh` directory and start a web server:
       ```bash
       cd ~/.ssh
       python3 -m http.server
       ```
     - On your **Android device**, open Termux and download the key:
       ```bash
       mkdir ~/.ssh
       curl http://<your-linux-pc-ip>:8000/id_rsa.pub >> ~/.ssh/authorized_keys
       ```
   - **Important:** Ensure the permissions are correct on your Android device:
     ```bash
     chmod 700 ~/.ssh
     chmod 600 ~/.ssh/authorized_keys
     ```
4. **Start the SSH server:** Start the SSH server in Termux:
   ```bash
   sshd
   ```
5. **Find the IP address:** Find the IP address of your Android device on the local network. You can do this by running the `ip addr` command in Termux.

### Linux (Client) Side

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```
2. **Install dependencies:**
   - **Debian/Ubuntu:** `sudo apt-get install redsocks socat`
   - **Arch Linux:** `sudo pacman -S redsocks socat`
   - **Other distributions:** Please refer to your distribution's package manager or compile from source.
3. **Make the client script executable:**
   ```bash
   chmod +x client/client.sh
   ```
4. **Run the client script:**
   ```bash
   sudo ./client/client.sh
   ```

## Usage

Once the setup is complete, all traffic from your Linux PC will be routed through your Android device's VPN connection. To stop the connection, simply press `Ctrl+C` in the terminal where the client script is running. The script will automatically and safely clean up the `iptables` rules and DNS settings.

## ⚠️ Warning

This script directly modifies `/etc/resolv.conf`. If your system uses a service like `systemd-resolved` or `NetworkManager` to manage DNS, this could cause unexpected behavior. The script creates a backup at `/etc/resolv.conf.bak` which is restored upon exit.

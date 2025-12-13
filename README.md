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
    * `openssh` installed (via project server script).
* **Linux PC:**
    * `ssh` client installed.
    * `sshuttle` installed (`sudo apt install sshuttle`).

## How it works

This project uses `sshuttle` to create a transparent proxy tunnel over SSH. All of your Linux PC's TCP and DNS traffic is forwarded through the Android device, which in turn routes it through its active VPN connection. This works without requiring root access on the Android device.

## Setup

### Android (Server) Side

1. **Install Termux:** Install the Termux app from the Google Play Store or F-Droid.
2. **Setup Server:** Copy the `server/server.sh` script to your Android device and run it.
   ```bash
   chmod +x server.sh
   ./server.sh
   ```
   This will install necessary packages (openssh) and start the server. It will display your Username and IP address.
3. **SSH Keys (Recommended):** For a smooth experience without typing passwords, copy your PC's public SSH key to the Android device (see standard SSH key setup guides).

### Linux (Client) Side

1. **Install sshuttle:**
   ```bash
   sudo apt install sshuttle
   ```
2. **Run the connection script:**
   ```bash
   ./connect.sh
   ```
3. **Enter Details:**
   - Enter the **IP Address** shown on the Android server script.
   - Enter the **Username** shown on the Android server script.
   - Enter your Android/SSH password if prompted (unless using SSH keys).

That's it! Your traffic is now routed through the Android device.

## Usage

To stop the connection, simply press `Ctrl+C` in the terminal where `connect.sh` is running. `sshuttle` safely restores your network settings automatically.

## ⚠️ Warning

This script directly modifies `/etc/resolv.conf`. If your system uses a service like `systemd-resolved` or `NetworkManager` to manage DNS, this could cause unexpected behavior. The script creates a backup at `/etc/resolv.conf.bak` which is restored upon exit.

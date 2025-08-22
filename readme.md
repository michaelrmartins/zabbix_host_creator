# Zabbix Host Creator - Installation and Usage Guide

## Overview
This is a Python web application that provides a beautiful interface for creating multiple Zabbix hosts from IP lists. The application connects to your Zabbix instance via API and creates hosts with auto-incrementing hostnames.

## Features
- ✅ Beautiful web interface with modern design
- ✅ Connect to Zabbix API with secure authentication
- ✅ Create multiple hosts from comma-separated IP lists
- ✅ Auto-increment hostnames (e.g., Tplink-01, Tplink-02)
- ✅ Select host groups from Zabbix via dropdown
- ✅ Real-time connection status
- ✅ Detailed results with success/error indicators
- ✅ Logging support
- ✅ Configuration file support

## Installation

### Prerequisites
- Python 3.7 or higher
- Debian/Ubuntu system (or any Linux distribution)
- Access to a Zabbix server with API enabled
- Zabbix user with host creation permissions

### Step 1: Install Python Dependencies
```bash
# Update system packages
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Create a virtual environment (recommended)
python3 -m venv zabbix-host-creator
cd zabbix-host-creator
source bin/activate

# Install required packages
pip install -r requirements.txt
```

### Step 2: Create Configuration File
Create a `config.ini` file in the same directory as the main script:

```ini
[zabbix]
# Zabbix server configuration
url = https://your-zabbix-server.com
username = your-zabbix-username
password = your-zabbix-password

[webserver]
# Web server configuration
host = 0.0.0.0
port = 5000
debug = false
```

**Important**: Replace the placeholder values with your actual Zabbix server details.

### Step 3: Set Up File Structure
Your directory should look like this:
```
zabbix-host-creator/
├── app.py (main application)
├── config.ini (your configuration)
├── requirements.txt
├── templates/
│   └── index.html (auto-created)
└── zabbix_host_creator.log (auto-created)
```

## Usage

### Starting the Application
```bash
# Make sure you're in the project directory and virtual environment is activated
python3 app.py
```

The application will start and display:
```
INFO - Starting Zabbix Host Creator on 0.0.0.0:5000
```

### Accessing the Web Interface
1. Open your web browser
2. Navigate to `http://your-server-ip:5000` (or `http://localhost:5000` if running locally)
3. You'll see the beautiful Zabbix Host Creator interface

### Creating Hosts

1. **Base Hostname**: Enter the base name for your hosts (e.g., "Tplink")
   - The system will create hosts as: Tplink-01, Tplink-02, etc.

2. **IP Addresses**: Enter comma-separated IP addresses
   - Example: `192.168.1.1, 192.168.1.2, 192.168.1.3`

3. **Host Group**: Select a host group from the dropdown
   - Groups are loaded automatically from your Zabbix server

4. **Test Connection**: Click to verify Zabbix connectivity

5. **Create Hosts**: Click to start the host creation process

### Example Usage
- **Base Hostname**: `Router`
- **IP Addresses**: `10.0.0.1, 10.0.0.2, 10.0.0.3`
- **Host Group**: `Network devices`

This will create:
- Router-01 (10.0.0.1)
- Router-02 (10.0.0.2)
- Router-03 (10.0.0.3)

## Configuration Options

### Zabbix Configuration
- `url`: Your Zabbix server URL (include https://)
- `username`: Zabbix user with API access
- `password`: Zabbix user password

### Web Server Configuration
- `host`: Server bind address (0.0.0.0 for all interfaces)
- `port`: Port number (default: 5000)
- `debug`: Enable debug mode (true/false)

## Security Considerations

1. **Firewall**: Ensure port 5000 (or your chosen port) is accessible
2. **SSL**: Consider using a reverse proxy (nginx/apache) with SSL
3. **Authentication**: The app uses Zabbix authentication, no additional auth needed
4. **Config File**: Keep config.ini secure with proper file permissions:
   ```bash
   chmod 600 config.ini
   ```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check Zabbix URL, username, and password
   - Verify Zabbix API is enabled
   - Check network connectivity

2. **Permission Denied**
   - Ensure Zabbix user has host creation permissions
   - Check user role and permissions in Zabbix

3. **Groups Not Loading**
   - Verify API authentication
   - Check if user has permission to read host groups

4. **Port Already in Use**
   - Change port in config.ini
   - Kill existing process: `sudo pkill -f "python3 app.py"`

### Logs
Check the log file `zabbix_host_creator.log` for detailed error information.

## Running as a Service (Optional)

To run the application as a system service:

1. Create a systemd service file:
```bash
sudo nano /etc/systemd/system/zabbix-host-creator.service
```

2. Add service configuration:
```ini
[Unit]
Description=Zabbix Host Creator
After=
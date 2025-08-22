# Update system packages
sudo apt update
sudo apt install python3 python3-pip python3-venv -y

# Create a virtual environment (recommended)
# python3 -m venv zabbix-host-creator
# cd zabbix-host-creator
# source bin/activate

# Install required packages
pip install -r requirements.txt
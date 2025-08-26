#!/usr/bin/env python3
"""
Zabbix Host Creator Web Application - Backend Only
A Flask-based web interface for creating multiple Zabbix hosts from IP lists
"""

import os
import sys
import configparser
import json
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for
from urllib3.exceptions import InsecureRequestWarning
import logging
from datetime import datetime

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zabbix_host_creator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

class ZabbixAPI:
    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Zabbix configuration
        self.zabbix_url = self.config.get('zabbix', 'url')
        self.zabbix_user = self.config.get('zabbix', 'username')
        self.zabbix_password = self.config.get('zabbix', 'password')
        self.zabbix_api_url = f"{self.zabbix_url}/api_jsonrpc.php"
        
        # Web server configuration
        self.web_host = self.config.get('webserver', 'host', fallback='0.0.0.0')
        self.web_port = self.config.getint('webserver', 'port', fallback=5000)
        self.web_debug = self.config.getboolean('webserver', 'debug', fallback=False)
        
        self.auth_token = None
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Zabbix Host Creator'
        }
        
    def authenticate(self):
        """Authenticate with Zabbix API"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "user.login",
                "params": {
                    "username": self.zabbix_user,
                    "password": self.zabbix_password
                },
                "id": 1
            }
            
            response = requests.post(
                self.zabbix_api_url,
                json=payload,
                headers=self.headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    self.auth_token = result['result']
                    logger.info("Successfully authenticated with Zabbix")
                    return True
                else:
                    logger.error(f"Authentication failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                logger.error(f"HTTP error during authentication: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Exception during authentication: {str(e)}")
            return False
    
    def get_host_groups(self):
        """Get all host groups from Zabbix"""
        if not self.auth_token:
            if not self.authenticate():
                return []
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "hostgroup.get",
                "params": {
                    "output": ["groupid", "name"],
                    "sortfield": "name"
                },
                "auth": self.auth_token,
                "id": 2
            }
            
            response = requests.post(
                self.zabbix_api_url,
                json=payload,
                headers=self.headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    return result['result']
                else:
                    logger.error(f"Error getting host groups: {result.get('error', 'Unknown error')}")
                    return []
            else:
                logger.error(f"HTTP error getting host groups: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Exception getting host groups: {str(e)}")
            return []
    
    def get_hosts_by_group(self, group_id):
        """Get hosts by group ID with their interfaces"""
        if not self.auth_token:
            if not self.authenticate():
                return []
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "host.get",
                "params": {
                    "output": ["hostid", "host", "name", "status"],
                    "groupids": [group_id],
                    "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type", "main"],
                    "sortfield": "name"
                },
                "auth": self.auth_token,
                "id": 4
            }
            
            response = requests.post(
                self.zabbix_api_url,
                json=payload,
                headers=self.headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    return result['result']
                else:
                    logger.error(f"Error getting hosts: {result.get('error', 'Unknown error')}")
                    return []
            else:
                logger.error(f"HTTP error getting hosts: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Exception getting hosts: {str(e)}")
            return []
    
    def create_host(self, hostname, ip_address, group_id, interface_type=1, interface_port=None):
        """Create a single host in Zabbix with specified interface type"""
        if not self.auth_token:
            if not self.authenticate():
                return False, "Authentication failed"
        
        # Default ports for each interface type
        default_ports = {
            1: "10050",  # Agent
            2: "161",    # SNMP
            3: "623",    # IPMI
            4: "12345"   # JMX
        }
        
        # Use provided port or default for interface type
        port = interface_port if interface_port else default_ports.get(interface_type, "10050")
        
        try:
            # Build interface configuration
            interface = {
                "type": interface_type,
                "main": 1,
                "useip": 1,
                "ip": ip_address,
                "dns": "",
                "port": str(port)
            }
            
            # Add interface-specific details for Zabbix 7.0
            if interface_type == 2:  # SNMP interface
                interface["details"] = {
                    "version": "2",  # SNMP version
                    "bulk": "1",     # Enable bulk requests
                    "community": "public"  # Default community string
                }
            elif interface_type == 3:  # IPMI interface
                interface["details"] = {
                    "username": "",
                    "password": ""
                }
            elif interface_type == 4:  # JMX interface
                interface["details"] = {
                    "username": "",
                    "password": ""
                }
            
            payload = {
                "jsonrpc": "2.0",
                "method": "host.create",
                "params": {
                    "host": hostname,
                    "name": hostname,
                    "groups": [{"groupid": group_id}],
                    "interfaces": [interface]
                },
                "auth": self.auth_token,
                "id": 3
            }
            
            response = requests.post(
                self.zabbix_api_url,
                json=payload,
                headers=self.headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    host_id = result['result']['hostids'][0]
                    interface_type_names = {1: "Agent", 2: "SNMP", 3: "IPMI", 4: "JMX"}
                    interface_name = interface_type_names.get(interface_type, "Unknown")
                    logger.info(f"Successfully created host {hostname} with ID {host_id} and {interface_name} interface on port {port}")
                    return True, f"Host {hostname} created successfully with {interface_name} interface"
                else:
                    error_msg = result.get('error', {}).get('data', 'Unknown error')
                    logger.error(f"Error creating host {hostname}: {error_msg}")
                    return False, f"Error creating host {hostname}: {error_msg}"
            else:
                logger.error(f"HTTP error creating host {hostname}: {response.status_code}")
                return False, f"HTTP error creating host {hostname}"
                
        except Exception as e:
            logger.error(f"Exception creating host {hostname}: {str(e)}")
            return False, f"Exception creating host {hostname}: {str(e)}"
    
    def add_interface_to_host(self, host_id, interface_type, ip_address, port, is_main=False):
        """Add interface to a specific host - Zabbix 7.0 compatible"""
        if not self.auth_token:
            if not self.authenticate():
                return False, "Authentication failed"
        
        try:
            # Base interface parameters according to Zabbix 7.0 documentation
            interface_params = {
                "hostid": str(host_id),
                "main": "1" if is_main else "0",  # Make it main if needed
                "type": str(interface_type),  # String value for interface type
                "useip": "1",  # String value
                "ip": str(ip_address),
                "dns": "",
                "port": str(port)
            }
            
            # Add interface-specific details for Zabbix 7.0
            if str(interface_type) == "2":  # SNMP interface
                interface_params["details"] = {
                    "version": "2",  # SNMP version as string
                    "bulk": "1",     # Enable bulk requests
                    "community": "public"  # Default community string
                }
            elif str(interface_type) == "3":  # IPMI interface
                interface_params["details"] = {
                    "username": "",
                    "password": ""
                }
            elif str(interface_type) == "4":  # JMX interface
                interface_params["details"] = {
                    "username": "",
                    "password": ""
                }
            
            payload = {
                "jsonrpc": "2.0",
                "method": "hostinterface.create",
                "params": interface_params,
                "auth": self.auth_token,
                "id": 5
            }
            
            response = requests.post(
                self.zabbix_api_url,
                json=payload,
                headers=self.headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    interface_id = result['result']['interfaceids'][0]
                    logger.info(f"Successfully added interface {interface_id} to host {host_id}")
                    return True, f"Interface added successfully"
                else:
                    error_msg = result.get('error', {})
                    error_data = error_msg.get('data', error_msg.get('message', 'Unknown error'))
                    logger.error(f"Error adding interface to host {host_id}: {error_data}")
                    return False, f"Error: {error_data}"
            else:
                logger.error(f"HTTP error adding interface to host {host_id}: {response.status_code}")
                return False, f"HTTP error occurred"
                
        except Exception as e:
            logger.error(f"Exception adding interface to host {host_id}: {str(e)}")
            return False, f"Exception: {str(e)}"
    
    def remove_interface_from_host(self, interface_id):
        """Remove interface from host"""
        if not self.auth_token:
            if not self.authenticate():
                return False, "Authentication failed"
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "hostinterface.delete",
                "params": [interface_id],
                "auth": self.auth_token,
                "id": 6
            }
            
            response = requests.post(
                self.zabbix_api_url,
                json=payload,
                headers=self.headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    logger.info(f"Successfully removed interface {interface_id}")
                    return True, f"Interface removed successfully"
                else:
                    error_msg = result.get('error', {}).get('data', 'Unknown error')
                    logger.error(f"Error removing interface {interface_id}: {error_msg}")
                    return False, f"Error: {error_msg}"
            else:
                logger.error(f"HTTP error removing interface {interface_id}: {response.status_code}")
                return False, f"HTTP error occurred"
                
        except Exception as e:
            logger.error(f"Exception removing interface {interface_id}: {str(e)}")
            return False, f"Exception: {str(e)}"
    
    def create_multiple_hosts(self, base_hostname, ip_list, group_id, use_ip_as_hostname=False, interface_type=1, interface_port=None):
        """Create multiple hosts from IP list with specified interface type"""
        results = []
        
        for i, ip in enumerate(ip_list, 1):
            ip_clean = ip.strip()
            
            if use_ip_as_hostname:
                # Use IP address as hostname directly (Zabbix 7.0 supports dots in hostnames)
                hostname = ip_clean
            else:
                # Use base hostname with sequential numbering
                hostname = f"{base_hostname}-{i:02d}"
            
            success, message = self.create_host(hostname, ip_clean, group_id, interface_type, interface_port)
            results.append({
                'hostname': hostname,
                'ip': ip_clean,
                'success': success,
                'message': message
            })
        
        return results
    
    def mass_update_interfaces(self, group_id, interface_type, port, operation):
        """Mass add or remove interfaces from all hosts in a group"""
        hosts = self.get_hosts_by_group(group_id)
        results = []
        
        for host in hosts:
            host_id = host['hostid']
            host_name = host['name']
            interfaces = host.get('interfaces', [])
            
            if operation == 'add':
                # Get IP from existing Agent interface (type 1) or first interface
                ip_address = None
                for interface in interfaces:
                    if interface['type'] == '1':  # Agent interface
                        ip_address = interface['ip']
                        break
                
                if not ip_address and interfaces:
                    ip_address = interfaces[0]['ip']
                
                if ip_address:
                    # Check if interface type already exists
                    interface_exists = any(int(iface['type']) == interface_type for iface in interfaces)
                    
                    if not interface_exists:
                        # Check if there's already a main interface of this type
                        has_main_interface = any(
                            int(iface['type']) == interface_type and iface['main'] == '1' 
                            for iface in interfaces
                        )
                        
                        # If no main interface of this type exists, make this one main
                        is_main = not has_main_interface
                        
                        success, message = self.add_interface_to_host(
                            host_id, interface_type, ip_address, port, is_main
                        )
                        results.append({
                            'host_name': host_name,
                            'operation': 'add',
                            'interface_type': interface_type,
                            'ip': ip_address,
                            'success': success,
                            'message': message
                        })
                    else:
                        results.append({
                            'host_name': host_name,
                            'operation': 'add',
                            'interface_type': interface_type,
                            'ip': ip_address,
                            'success': False,
                            'message': 'Interface type already exists'
                        })
                else:
                    results.append({
                        'host_name': host_name,
                        'operation': 'add',
                        'interface_type': interface_type,
                        'ip': 'N/A',
                        'success': False,
                        'message': 'No IP address found'
                    })
            
            elif operation == 'remove':
                # Find interfaces of the specified type (non-main interfaces only)
                interfaces_to_remove = [
                    iface for iface in interfaces 
                    if int(iface['type']) == interface_type and iface['main'] == '0'
                ]
                
                if interfaces_to_remove:
                    for interface in interfaces_to_remove:
                        success, message = self.remove_interface_from_host(interface['interfaceid'])
                        results.append({
                            'host_name': host_name,
                            'operation': 'remove',
                            'interface_type': interface_type,
                            'ip': interface['ip'],
                            'success': success,
                            'message': message
                        })
                else:
                    results.append({
                        'host_name': host_name,
                        'operation': 'remove',
                        'interface_type': interface_type,
                        'ip': 'N/A',
                        'success': False,
                        'message': 'No removable interface found'
                    })
        
        return results

# Initialize Zabbix API
zabbix_api = ZabbixAPI()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/groups')
def get_groups():
    """API endpoint to get Zabbix host groups"""
    groups = zabbix_api.get_host_groups()
    return jsonify(groups)

@app.route('/api/hosts_by_group/<group_id>')
def get_hosts_by_group(group_id):
    """API endpoint to get hosts by group"""
    hosts = zabbix_api.get_hosts_by_group(group_id)
    return jsonify(hosts)

@app.route('/api/create_hosts', methods=['POST'])
def create_hosts():
    """API endpoint to create hosts with specified interface type"""
    try:
        data = request.get_json()
        
        # Check if using IP as hostname
        use_ip_as_hostname = data.get('use_ip_as_hostname', False)
        
        # Get interface type and port
        interface_type = int(data.get('interface_type', 1))  # Default to Agent
        interface_port = data.get('interface_port')  # Can be None for default
        
        # Validate input based on mode
        if not use_ip_as_hostname and not data.get('base_hostname'):
            return jsonify({'error': 'Base hostname is required when not using IP as hostname'}), 400
        
        if not data.get('ip_list'):
            return jsonify({'error': 'IP list is required'}), 400
        
        if not data.get('group_id'):
            return jsonify({'error': 'Group ID is required'}), 400
        
        # Parse IP list
        ip_list = [ip.strip() for ip in data['ip_list'].split(',') if ip.strip()]
        
        if not ip_list:
            return jsonify({'error': 'No valid IPs provided'}), 400
        
        # Create hosts with specified interface type
        results = zabbix_api.create_multiple_hosts(
            data.get('base_hostname', ''),
            ip_list,
            data['group_id'],
            use_ip_as_hostname,
            interface_type,
            interface_port
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'total': len(results),
                'successful': len([r for r in results if r['success']]),
                'failed': len([r for r in results if not r['success']])
            }
        })
        
    except Exception as e:
        logger.error(f"Error in create_hosts endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mass_update_interfaces', methods=['POST'])
def mass_update_interfaces():
    """API endpoint for mass interface updates"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data.get('group_id'):
            return jsonify({'error': 'Group ID is required'}), 400
        
        if not data.get('interface_type'):
            return jsonify({'error': 'Interface type is required'}), 400
        
        if not data.get('operation') or data['operation'] not in ['add', 'remove']:
            return jsonify({'error': 'Operation must be "add" or "remove"'}), 400
        
        # Default ports for interface types
        port_map = {
            1: "10050",  # Agent
            2: "161",    # SNMP
            3: "623",    # IPMI
            4: "12345"   # JMX
        }
        
        port = data.get('port', port_map.get(int(data['interface_type']), "10050"))
        
        # Perform mass update
        results = zabbix_api.mass_update_interfaces(
            data['group_id'],
            int(data['interface_type']),
            port,
            data['operation']
        )
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'total': len(results),
                'successful': len([r for r in results if r['success']]),
                'failed': len([r for r in results if not r['success']])
            }
        })
        
    except Exception as e:
        logger.error(f"Error in mass_update_interfaces endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test_connection')
def test_connection():
    """Test Zabbix connection"""
    success = zabbix_api.authenticate()
    return jsonify({'success': success})

@app.template_filter('datetime')
def datetime_filter(timestamp):
    """Format datetime for templates"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

# Create templates and static directories if they don't exist
if not os.path.exists('templates'):
    os.makedirs('templates')
if not os.path.exists('static'):
    os.makedirs('static')

if __name__ == '__main__':
    # Check if config file exists
    if not os.path.exists('config.ini'):
        print("Config file 'config.ini' not found. Please create it first.")
        sys.exit(1)
    
    # Start the web server
    logger.info(f"Starting Zabbix Host Creator on {zabbix_api.web_host}:{zabbix_api.web_port}")
    app.run(
        host=zabbix_api.web_host,
        port=zabbix_api.web_port,
        debug=zabbix_api.web_debug
    )
#!/usr/bin/env python3
"""
Zabbix Host Creator Web Application
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
    
    def create_host(self, hostname, ip_address, group_id):
        """Create a single host in Zabbix"""
        if not self.auth_token:
            if not self.authenticate():
                return False, "Authentication failed"
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "host.create",
                "params": {
                    "host": hostname,
                    "name": hostname,
                    "groups": [{"groupid": group_id}],
                    "interfaces": [
                        {
                            "type": 1,  # Agent interface
                            "main": 1,
                            "useip": 1,
                            "ip": ip_address,
                            "dns": "",
                            "port": "10050"
                        }
                    ]
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
                    logger.info(f"Successfully created host {hostname} with ID {host_id}")
                    return True, f"Host {hostname} created successfully"
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
    
    def create_multiple_hosts(self, base_hostname, ip_list, group_id):
        """Create multiple hosts from IP list"""
        results = []
        
        for i, ip in enumerate(ip_list, 1):
            hostname = f"{base_hostname}-{i:02d}"
            success, message = self.create_host(hostname, ip.strip(), group_id)
            results.append({
                'hostname': hostname,
                'ip': ip.strip(),
                'success': success,
                'message': message
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

@app.route('/api/create_hosts', methods=['POST'])
def create_hosts():
    """API endpoint to create hosts"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data.get('base_hostname'):
            return jsonify({'error': 'Base hostname is required'}), 400
        
        if not data.get('ip_list'):
            return jsonify({'error': 'IP list is required'}), 400
        
        if not data.get('group_id'):
            return jsonify({'error': 'Group ID is required'}), 400
        
        # Parse IP list
        ip_list = [ip.strip() for ip in data['ip_list'].split(',') if ip.strip()]
        
        if not ip_list:
            return jsonify({'error': 'No valid IPs provided'}), 400
        
        # Create hosts
        results = zabbix_api.create_multiple_hosts(
            data['base_hostname'],
            ip_list,
            data['group_id']
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

@app.route('/api/test_connection')
def test_connection():
    """Test Zabbix connection"""
    success = zabbix_api.authenticate()
    return jsonify({'success': success})

@app.template_filter('datetime')
def datetime_filter(timestamp):
    """Format datetime for templates"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

# Create templates directory if it doesn't exist
if not os.path.exists('templates'):
    os.makedirs('templates')

# HTML Template
html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zabbix Host Creator</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 800px;
            width: 100%;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .header h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        
        .form-group {
            margin-bottom: 25px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }
        
        input[type="text"], select, textarea {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        textarea {
            resize: vertical;
            height: 120px;
        }
        
        .button-group {
            display: flex;
            gap: 15px;
            margin-top: 30px;
        }
        
        button {
            flex: 1;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: #f8f9fa;
            color: #333;
            border: 2px solid #e1e5e9;
        }
        
        .btn-secondary:hover {
            background: #e9ecef;
        }
        
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            display: none;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .results {
            margin-top: 20px;
            display: none;
        }
        
        .results-header {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px 10px 0 0;
            border-bottom: 1px solid #e1e5e9;
        }
        
        .results-body {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #e1e5e9;
            border-radius: 0 0 10px 10px;
        }
        
        .result-item {
            padding: 10px 15px;
            border-bottom: 1px solid #f1f3f4;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .result-item:last-child {
            border-bottom: none;
        }
        
        .result-success {
            color: #28a745;
        }
        
        .result-error {
            color: #dc3545;
        }
        
        .spinner {
            display: none;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
        }
        
        .connection-status.connected {
            background: #d4edda;
            color: #155724;
        }
        
        .connection-status.disconnected {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖥️ Zabbix Host Creator</h1>
            <p>Create multiple Zabbix hosts from IP lists with ease</p>
        </div>
        
        <form id="hostForm">
            <div class="form-group">
                <label for="base_hostname">Base Hostname:</label>
                <input type="text" id="base_hostname" name="base_hostname" placeholder="e.g., Tplink" required>
                <small style="color: #666; margin-top: 5px; display: block;">
                    Hosts will be created as: Tplink-01, Tplink-02, etc.
                </small>
            </div>
            
            <div class="form-group">
                <label for="ip_list">IP Addresses (comma-separated):</label>
                <textarea id="ip_list" name="ip_list" placeholder="192.168.1.1, 192.168.1.2, 192.168.1.3" required></textarea>
            </div>
            
            <div class="form-group">
                <label for="group_id">Zabbix Host Group:</label>
                <select id="group_id" name="group_id" required>
                    <option value="">Loading groups...</option>
                </select>
            </div>
            
            <div class="button-group">
                <button type="button" id="testBtn" class="btn-secondary">Test Connection</button>
                <button type="submit" id="createBtn" class="btn-primary">Create Hosts</button>
            </div>
        </form>
        
        <div class="spinner" id="spinner"></div>
        
        <div class="status" id="status"></div>
        
        <div class="results" id="results">
            <div class="results-header">
                <h3 id="resultsTitle">Results</h3>
            </div>
            <div class="results-body" id="resultsBody"></div>
        </div>
    </div>
    
    <div class="connection-status" id="connectionStatus">
        Checking connection...
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            loadGroups();
            testConnection();
            
            document.getElementById('testBtn').addEventListener('click', testConnection);
            document.getElementById('hostForm').addEventListener('submit', createHosts);
        });
        
        function showStatus(message, isError = false) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + (isError ? 'error' : 'success');
            status.style.display = 'block';
            
            setTimeout(() => {
                status.style.display = 'none';
            }, 5000);
        }
        
        function showSpinner(show = true) {
            document.getElementById('spinner').style.display = show ? 'block' : 'none';
        }
        
        function loadGroups() {
            fetch('/api/groups')
                .then(response => response.json())
                .then(groups => {
                    const select = document.getElementById('group_id');
                    select.innerHTML = '<option value="">Select a group...</option>';
                    
                    groups.forEach(group => {
                        const option = document.createElement('option');
                        option.value = group.groupid;
                        option.textContent = group.name;
                        select.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('Error loading groups:', error);
                    showStatus('Error loading groups: ' + error.message, true);
                });
        }
        
        function testConnection() {
            const statusElement = document.getElementById('connectionStatus');
            statusElement.textContent = 'Testing connection...';
            statusElement.className = 'connection-status';
            
            fetch('/api/test_connection')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        statusElement.textContent = '✅ Connected to Zabbix';
                        statusElement.className = 'connection-status connected';
                        showStatus('Successfully connected to Zabbix!');
                    } else {
                        statusElement.textContent = '❌ Connection Failed';
                        statusElement.className = 'connection-status disconnected';
                        showStatus('Failed to connect to Zabbix. Check configuration.', true);
                    }
                })
                .catch(error => {
                    statusElement.textContent = '❌ Connection Error';
                    statusElement.className = 'connection-status disconnected';
                    showStatus('Connection error: ' + error.message, true);
                });
        }
        
        function createHosts(event) {
            event.preventDefault();
            
            const formData = new FormData(event.target);
            const data = {
                base_hostname: formData.get('base_hostname'),
                ip_list: formData.get('ip_list'),
                group_id: formData.get('group_id')
            };
            
            showSpinner(true);
            document.getElementById('createBtn').disabled = true;
            
            fetch('/api/create_hosts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                showSpinner(false);
                document.getElementById('createBtn').disabled = false;
                
                if (data.success) {
                    showResults(data.results, data.summary);
                    showStatus(`Successfully created ${data.summary.successful} of ${data.summary.total} hosts!`);
                } else {
                    showStatus('Error: ' + data.error, true);
                }
            })
            .catch(error => {
                showSpinner(false);
                document.getElementById('createBtn').disabled = false;
                showStatus('Error: ' + error.message, true);
            });
        }
        
        function showResults(results, summary) {
            const resultsDiv = document.getElementById('results');
            const resultsTitle = document.getElementById('resultsTitle');
            const resultsBody = document.getElementById('resultsBody');
            
            resultsTitle.textContent = `Results (${summary.successful}/${summary.total} successful)`;
            resultsBody.innerHTML = '';
            
            results.forEach(result => {
                const item = document.createElement('div');
                item.className = 'result-item';
                item.innerHTML = `
                    <div>
                        <strong>${result.hostname}</strong> (${result.ip})
                    </div>
                    <div class="${result.success ? 'result-success' : 'result-error'}">
                        ${result.success ? '✅' : '❌'} ${result.message}
                    </div>
                `;
                resultsBody.appendChild(item);
            });
            
            resultsDiv.style.display = 'block';
        }
    </script>
</body>
</html>'''

# Write the HTML template
with open('templates/index.html', 'w') as f:
    f.write(html_template)

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
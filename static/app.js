// Global variables
let useIpAsHostname = false;
let currentHosts = [];

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    loadGroups();
    testConnection();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('testBtn').addEventListener('click', testConnection);
    document.getElementById('hostForm').addEventListener('submit', createHosts);
    document.getElementById('interfaceForm').addEventListener('submit', updateInterfaces);
    document.getElementById('ipToggle').addEventListener('click', toggleHostnameMode);
    document.getElementById('loadHostsBtn').addEventListener('click', loadHosts);
    document.getElementById('interface_type').addEventListener('change', updateDefaultPort);
}

// Tab management
function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => content.classList.remove('active'));
    
    // Remove active class from all tabs
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Show selected tab content
    document.getElementById(tabName).classList.add('active');
    
    // Add active class to clicked tab
    event.target.classList.add('active');
    
    // Load groups for interface tab if needed
    if (tabName === 'host-interface') {
        loadInterfaceGroups();
    }
}

// Update default port based on interface type
function updateDefaultPort() {
    const interfaceType = document.getElementById('interface_type').value;
    const portInput = document.getElementById('interface_port');
    
    const defaultPorts = {
        '1': '10050',  // Agent
        '2': '161',    // SNMP
        '3': '623',    // IPMI
        '4': '12345'   // JMX
    };
    
    portInput.value = defaultPorts[interfaceType] || '10050';
}

// Toggle hostname mode (IP vs Base hostname)
function toggleHostnameMode() {
    const toggle = document.getElementById('ipToggle');
    const hostnameInput = document.getElementById('base_hostname');
    const hostnameHelp = document.getElementById('hostnameHelp');
    
    useIpAsHostname = !useIpAsHostname;
    
    if (useIpAsHostname) {
        toggle.classList.add('active');
        hostnameInput.disabled = true;
        hostnameInput.required = false;
        hostnameInput.value = '';
        hostnameHelp.textContent = 'Hosts will be created using IP addresses as hostnames (e.g., 192.168.1.1, 192.168.1.2)';
    } else {
        toggle.classList.remove('active');
        hostnameInput.disabled = false;
        hostnameInput.required = true;
        hostnameHelp.textContent = 'Hosts will be created as: Tplink-01, Tplink-02, etc.';
    }
}

// UI helper functions
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

// API functions
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

function loadInterfaceGroups() {
    fetch('/api/groups')
        .then(response => response.json())
        .then(groups => {
            const select = document.getElementById('interface_group_id');
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

function loadHosts() {
    const groupId = document.getElementById('interface_group_id').value;
    if (!groupId) {
        showStatus('Please select a host group first', true);
        return;
    }
    
    showSpinner(true);
    
    fetch('/api/hosts_by_group/' + groupId)
        .then(response => response.json())
        .then(hosts => {
            showSpinner(false);
            currentHosts = hosts;
            displayHosts(hosts);
        })
        .catch(error => {
            showSpinner(false);
            console.error('Error loading hosts:', error);
            showStatus('Error loading hosts: ' + error.message, true);
        });
}

function displayHosts(hosts) {
    const hostList = document.getElementById('hostList');
    const hostListContent = document.getElementById('hostListContent');
    
    if (hosts.length === 0) {
        hostListContent.innerHTML = '<div class="host-item"><div class="host-info">No hosts found in this group</div></div>';
        hostList.style.display = 'block';
        return;
    }
    
    hostListContent.innerHTML = '';
    
    hosts.forEach(host => {
        const hostDiv = document.createElement('div');
        hostDiv.className = 'host-item';
        
        const interfaceTypes = {
            '1': { name: 'Agent', class: 'interface-agent' },
            '2': { name: 'SNMP', class: 'interface-snmp' },
            '3': { name: 'IPMI', class: 'interface-ipmi' },
            '4': { name: 'JMX', class: 'interface-jmx' }
        };
        
        let interfaceBadges = '';
        if (host.interfaces && host.interfaces.length > 0) {
            host.interfaces.forEach(iface => {
                const ifaceType = interfaceTypes[iface.type] || { name: 'Unknown', class: '' };
                interfaceBadges += '<span class="interface-badge ' + ifaceType.class + '">' + ifaceType.name + ':' + iface.port + '</span>';
            });
        } else {
            interfaceBadges = '<span class="interface-badge">No interfaces</span>';
        }
        
        hostDiv.innerHTML = '<div class="host-info">' +
            '<div class="host-name">' + (host.name || host.host) + '</div>' +
            '<div class="host-interfaces">' + interfaceBadges + '</div>' +
            '</div>';
        
        hostListContent.appendChild(hostDiv);
    });
    
    hostList.style.display = 'block';
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
        group_id: formData.get('group_id'),
        use_ip_as_hostname: useIpAsHostname
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
            showStatus('Successfully created ' + data.summary.successful + ' of ' + data.summary.total + ' hosts!');
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

function updateInterfaces(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = {
        group_id: formData.get('interface_group_id'),
        interface_type: formData.get('interface_type'),
        port: formData.get('interface_port'),
        operation: formData.get('operation')
    };
    
    if (!data.group_id) {
        showStatus('Please select a host group', true);
        return;
    }
    
    showSpinner(true);
    document.getElementById('updateInterfacesBtn').disabled = true;
    
    fetch('/api/mass_update_interfaces', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        showSpinner(false);
        document.getElementById('updateInterfacesBtn').disabled = false;
        
        if (data.success) {
            showResults(data.results, data.summary, true);
            const operation = data.results[0] ? data.results[0].operation : 'updated';
            showStatus('Successfully ' + operation + ' ' + data.summary.successful + ' of ' + data.summary.total + ' interfaces!');
            // Reload hosts to show updated interfaces
            if (currentHosts.length > 0) {
                loadHosts();
            }
        } else {
            showStatus('Error: ' + data.error, true);
        }
    })
    .catch(error => {
        showSpinner(false);
        document.getElementById('updateInterfacesBtn').disabled = false;
        showStatus('Error: ' + error.message, true);
    });
}

function showResults(results, summary, isInterface) {
    const resultsDiv = document.getElementById('results');
    const resultsTitle = document.getElementById('resultsTitle');
    const resultsBody = document.getElementById('resultsBody');
    
    const operation = isInterface ? 'interface operations' : 'hosts';
    resultsTitle.textContent = 'Results (' + summary.successful + '/' + summary.total + ' successful ' + operation + ')';
    resultsBody.innerHTML = '';
    
    results.forEach(result => {
        const item = document.createElement('div');
        item.className = 'result-item';
        
        let itemContent;
        if (isInterface) {
            const interfaceTypes = { '1': 'Agent', '2': 'SNMP', '3': 'IPMI', '4': 'JMX' };
            const interfaceTypeName = interfaceTypes[result.interface_type] || 'Unknown';
            
            itemContent = '<div>' +
                '<strong>' + result.host_name + '</strong> (' + result.ip + ') - ' + interfaceTypeName + ' Interface' +
                '</div>' +
                '<div class="' + (result.success ? 'result-success' : 'result-error') + '">' +
                (result.success ? '✅' : '❌') + ' ' + result.message +
                '</div>';
        } else {
            itemContent = '<div>' +
                '<strong>' + result.hostname + '</strong> (' + result.ip + ')' +
                '</div>' +
                '<div class="' + (result.success ? 'result-success' : 'result-error') + '">' +
                (result.success ? '✅' : '❌') + ' ' + result.message +
                '</div>';
        }
        
        item.innerHTML = itemContent;
        resultsBody.appendChild(item);
    });
    
    resultsDiv.style.display = 'block';
}
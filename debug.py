#!/usr/bin/env python3
"""
Debug script to test Zabbix Host Creator
"""

import sys
import os

print("=" * 60)
print("ZABBIX HOST CREATOR - DEBUG SCRIPT")
print("=" * 60)

# Check Python version
print(f"\n1. Python Version: {sys.version}")
if sys.version_info < (3, 6):
    print("   ❌ ERROR: Python 3.6 or higher is required!")
    sys.exit(1)
else:
    print("   ✅ Python version is OK")

# Check if config.ini exists
print("\n2. Checking config.ini...")
if os.path.exists('config.ini'):
    print("   ✅ config.ini found")
    # Try to read it
    try:
        import configparser
        config = configparser.ConfigParser()
        config.read('config.ini')
        print(f"   - Zabbix URL: {config.get('zabbix', 'url')}")
        print(f"   - Username: {config.get('zabbix', 'username')}")
        print("   - Password: [HIDDEN]")
    except Exception as e:
        print(f"   ❌ Error reading config.ini: {e}")
else:
    print("   ❌ config.ini NOT found!")
    print("   Creating example config.ini...")
    with open('config.ini', 'w') as f:
        f.write("""[zabbix]
# Zabbix server configuration
url = http://your-zabbix-server.com/zabbix
username = your-username
password = your-password

[webserver]
# Web server configuration
host = 0.0.0.0
port = 5000
debug = false
""")
    print("   📝 Please edit config.ini with your Zabbix credentials")

# Check required packages
print("\n3. Checking required Python packages...")
packages = {
    'flask': 'Flask',
    'requests': 'requests',
    'urllib3': 'urllib3'
}

missing_packages = []
for module, package in packages.items():
    try:
        __import__(module)
        print(f"   ✅ {package} is installed")
    except ImportError:
        print(f"   ❌ {package} is NOT installed")
        missing_packages.append(package)

if missing_packages:
    print(f"\n   ⚠️  Missing packages: {', '.join(missing_packages)}")
    print("   Run: pip install " + " ".join(missing_packages))
    sys.exit(1)

# Check if templates directory exists
print("\n4. Checking directories...")
dirs_to_check = ['templates', 'static']
for dir_name in dirs_to_check:
    if os.path.exists(dir_name):
        print(f"   ✅ {dir_name}/ exists")
    else:
        print(f"   ⚠️  {dir_name}/ does not exist, creating...")
        os.makedirs(dir_name)
        print(f"   ✅ {dir_name}/ created")

# Check if HTML template exists
print("\n5. Checking template files...")
if os.path.exists('templates/index.html'):
    print("   ✅ templates/index.html exists")
else:
    print("   ❌ templates/index.html NOT found!")
    print("   Please ensure index.html is in the templates/ directory")

# Check if static files exist
if os.path.exists('static/app.js'):
    print("   ✅ static/app.js exists")
else:
    print("   ⚠️  static/app.js NOT found")
    
if os.path.exists('static/styles.css'):
    print("   ✅ static/styles.css exists")
else:
    print("   ⚠️  static/styles.css NOT found")

# Try to import and test the app
print("\n6. Testing app.py import...")
try:
    # Try importing the main app
    import app
    print("   ✅ app.py imported successfully")
    
    # Check if Flask app is created
    if hasattr(app, 'app'):
        print("   ✅ Flask app object found")
    else:
        print("   ❌ Flask app object not found")
        
    # Check if ZabbixAPI is created
    if hasattr(app, 'zabbix_api'):
        print("   ✅ ZabbixAPI object found")
    else:
        print("   ❌ ZabbixAPI object not found")
        
except SyntaxError as e:
    print(f"   ❌ SYNTAX ERROR in app.py:")
    print(f"      Line {e.lineno}: {e.msg}")
    print(f"      {e.text}")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Error importing app.py: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)

# If everything is OK, ask if user wants to start the app
if not missing_packages:
    print("\n✅ All checks passed!")
    response = input("\nDo you want to start the application now? (y/n): ")
    if response.lower() == 'y':
        print("\nStarting Zabbix Host Creator...")
        print("Press Ctrl+C to stop\n")
        try:
            import app
            app.app.run(
                host=app.zabbix_api.web_host,
                port=app.zabbix_api.web_port,
                debug=True  # Enable debug mode for testing
            )
        except KeyboardInterrupt:
            print("\n\nApplication stopped.")
        except Exception as e:
            print(f"\n❌ Error starting application: {e}")
            import traceback
            traceback.print_exc()
else:
    print("\n❌ Please install missing packages first!")
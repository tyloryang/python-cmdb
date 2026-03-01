import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_servers():
    # 1. Login
    print("Attempting to login...")
    login_res = requests.post(f"{BASE_URL}/api/v1/auth/login", data={
        "username": "admin",
        "password": "123456"
    })
    
    if login_res.status_code != 200:
        print(f"Login failed: {login_res.text}")
        return
    
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login success.")

    ips = ["192.168.9.221", "192.168.9.222", "192.168.9.223", "192.168.9.224"]
    
    for ip in ips:
        print(f"\nCreating server {ip}...")
        # Note: We use the IP as hostname since no hostname was provided
        server_data = {
            "hostname": ip,
            "ssh_port": 22,
            "ssh_user": "root",
            "ssh_auth_type": "password",
            "ssh_credential": "Yangys@55",
            "status": "running"
        }
        
        create_res = requests.post(
            f"{BASE_URL}/api/v1/cmdb/servers", 
            json=server_data, 
            headers=headers
        )
        
        if create_res.status_code in (201, 200):
            server_id = create_res.json()["id"]
            print(f"Server {ip} created with ID: {server_id}")
            
            # 2. Test Ping (SSH connectivity)
            print(f"Testing SSH connectivity for {ip}...")
            ping_res = requests.post(
                f"{BASE_URL}/api/v1/cmdb/servers/{server_id}/ping",
                headers=headers
            )
            if ping_res.status_code == 200:
                print(f"SSH Test Success: {ping_res.json().get('msg')}")
            else:
                print(f"SSH Test Failed: {ping_res.text}")
        else:
            print(f"Failed to create server {ip}: {create_res.text}")

if __name__ == "__main__":
    test_servers()

#!/usr/bin/env python3
import os
import sys
import time
import socket
import psycopg

def wait_for_db():
    # Try multiple methods to find the database
    host = os.environ.get('POSTGRES_HOST', 'db')
    port = int(os.environ.get('POSTGRES_PORT', '5432'))
    user = os.environ.get('POSTGRES_USER', 'fallguard')
    password = os.environ.get('POSTGRES_PASSWORD', 'fallguard')
    database = os.environ.get('POSTGRES_DB', 'fallguard')
    
    # Known Docker network IPs for the db service (based on network inspection)
    # The mlproject_default network uses 172.19.0.0/16
    # db container is typically at 172.19.0.3
    db_ips = [
        '172.19.0.3',  # Primary IP for db in mlproject_default network
        '172.19.0.2',  # Alternative
        '172.19.0.4',  # Alternative
        host,  # Try hostname as last resort
    ]
    
    print(f"Attempting to connect to database (port {port})")
    
    # Initial delay
    print("Waiting for network to settle...")
    time.sleep(5)
    
    max_retries = 30
    retry_interval = 5
    
    for i in range(max_retries):
        for db_ip in db_ips:
            try:
                if db_ip == host:
                    # Try DNS resolution
                    try:
                        ip = socket.gethostbyname(host)
                        print(f"DNS resolved {host} -> {ip}")
                        db_ip = ip
                    except socket.gaierror:
                        continue
                
                print(f"Attempt {i+1}/{max_retries}: Trying {db_ip}:{port}...")
                
                # Test TCP connection
                sock = socket.create_connection((db_ip, port), timeout=5)
                sock.close()
                print(f"TCP connection to {db_ip}:{port} successful")
                
                # Test PostgreSQL connection
                conn = psycopg.connect(
                    host=db_ip,
                    port=port,
                    user=user,
                    password=password,
                    dbname=database,
                    connect_timeout=10
                )
                conn.close()
                print(f"Database connection successful at {db_ip}!")
                return True
                
            except socket.timeout:
                print(f"  {db_ip}: Connection timeout")
            except ConnectionRefusedError:
                print(f"  {db_ip}: Connection refused")
            except Exception as e:
                print(f"  {db_ip}: {e}")
        
        if i < max_retries - 1:
            time.sleep(retry_interval)
    
    print("Failed to connect to database after maximum retries")
    return False

if __name__ == '__main__':
    success = wait_for_db()
    sys.exit(0 if success else 1)
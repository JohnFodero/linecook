#!/usr/bin/env python3
"""
Simple test script for the LineCook FastAPI application
"""
import requests
import sys
from pathlib import Path

def test_health_endpoint():
    """Test the health check endpoint"""
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Health check: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ Server not running. Start with: uv run python main.py server")
        return False

def test_create_labels(file_path: str, print_flag: bool = False):
    """Test the create_labels endpoint with a file"""
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'print_label_flag': print_flag}
            response = requests.post("http://localhost:8000/create_labels", files=files, data=data)
        
        print(f"Create labels: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ Server not running. Start with: uv run python main.py server")
        return False

if __name__ == "__main__":
    print("Testing LineCook FastAPI...")
    
    # Test health endpoint
    if not test_health_endpoint():
        sys.exit(1)
    
    # Test with sample files if they exist
    test_files = [
        "test_inputs/amazon.jpg",
        "test_inputs/googlelabel.png"
    ]
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"\nTesting with {test_file}...")
            test_create_labels(test_file)
            break
    else:
        print("\nNo test files found in test_inputs/")
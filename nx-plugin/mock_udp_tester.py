import socket
import json
import time
import math

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Sending mock UDP packets to {UDP_IP}:{UDP_PORT}...")
print("This will simulate panning left and right, then rotating.")

try:
    for i in range(50):
        # Pan back and forth
        dx = math.sin(i * 0.2) * 0.05
        msg = {"gesture": "PAN", "dx": dx, "dy": 0.0, "dz": 0.0}
        sock.sendto(json.dumps(msg).encode('utf-8'), (UDP_IP, UDP_PORT))
        print(f"Sent: {msg}")
        time.sleep(0.1)
        
    for i in range(50):
        # Rotate back and forth
        dx = math.sin(i * 0.2) * 0.05
        msg = {"gesture": "ROTATE", "dx": dx, "dy": 0.0, "dz": 0.0}
        sock.sendto(json.dumps(msg).encode('utf-8'), (UDP_IP, UDP_PORT))
        print(f"Sent: {msg}")
        time.sleep(0.1)

    print("Mock test completed.")
except KeyboardInterrupt:
    print("Stopped.")
finally:
    sock.close()

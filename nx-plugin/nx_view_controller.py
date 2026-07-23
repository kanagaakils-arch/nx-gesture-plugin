import NXOpen
import NXOpen.UF
import socket
import json
import time
import os

def main():
    session = NXOpen.Session.GetSession()
    uf = NXOpen.UF.UFSession.GetUFSession()
    
    work_part = session.Parts.Work
    if work_part is None:
        uf.Ui.SetStatus("No active part to control.")
        return
        
    work_view = session.Parts.Display.ModelingViews.WorkView
    
    # Load configuration
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        uf.Ui.SetStatus(f"Error loading config.json: {e}")
        return

    UDP_IP = config["network"]["udp_ip"]
    UDP_PORT = config["network"]["udp_port"]
    
    ROT_SENSITIVITY = config["sensitivity"]["rotate"]
    PAN_SENSITIVITY = config["sensitivity"]["pan"]
    ZOOM_SENSITIVITY = config["sensitivity"]["zoom"]
    ROLL_SENSITIVITY = config["sensitivity"]["roll"]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    
    uf.Ui.SetStatus(f"NX Gesture Control Active. Listening on port {UDP_PORT}...")

    try:
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                msg = json.loads(data.decode('utf-8'))
                
                gesture = msg.get("gesture", "IDLE")
                dx = msg.get("dx", 0.0)
                dy = msg.get("dy", 0.0)
                dz = msg.get("dz", 0.0)
                droll = msg.get("droll", 0.0)
                
                needs_update = False
                
                if gesture == "RESET_VIEW":
                    work_view.Orient(NXOpen.View.ExtendedViewType.Trimetric)
                    work_view.Fit()
                    needs_update = True
                    
                elif gesture == "FIT":
                    work_view.Fit()
                    needs_update = True
                    
                elif gesture == "ROTATE":
                    center = work_view.AbsoluteOrigin
                    if abs(dx) > 0.001:
                        axis_y = NXOpen.Vector3d(0.0, 1.0, 0.0)
                        angle_y = dx * ROT_SENSITIVITY
                        work_view.Concatenate(1.0, center, axis_y, angle_y)
                        needs_update = True
                    if abs(dy) > 0.001:
                        axis_x = NXOpen.Vector3d(1.0, 0.0, 0.0)
                        angle_x = dy * ROT_SENSITIVITY
                        work_view.Concatenate(1.0, center, axis_x, angle_x)
                        needs_update = True
                        
                elif gesture == "ROLL":
                    if abs(droll) > 0.001:
                        center = work_view.AbsoluteOrigin
                        axis_z = NXOpen.Vector3d(0.0, 0.0, 1.0)
                        angle_z = droll * ROLL_SENSITIVITY
                        work_view.Concatenate(1.0, center, axis_z, angle_z)
                        needs_update = True
                        
                elif gesture == "PAN":
                    if abs(dx) > 0.001 or abs(dy) > 0.001:
                        uf.View.Pan(work_view.Name, -dx * PAN_SENSITIVITY, -dy * PAN_SENSITIVITY)
                        needs_update = True
                        
                elif gesture == "ZOOM":
                    if abs(dz) > 0.001:
                        scale = 1.0 + (dz * ZOOM_SENSITIVITY)
                        if scale > 0.1:
                            axis_z = NXOpen.Vector3d(0.0, 0.0, 1.0)
                            work_view.Concatenate(scale, work_view.AbsoluteOrigin, axis_z, 0.0)
                            needs_update = True
                
                if needs_update:
                    uf.Disp.RegenerateDisplay()
                    
            except socket.error:
                pass
            except Exception as e:
                pass
                
            time.sleep(0.01)
            
    except Exception as e:
        uf.Ui.SetStatus("NX Gesture Control Stopped.")

if __name__ == '__main__':
    main()

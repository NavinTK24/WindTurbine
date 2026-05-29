import bpy
import urllib.request
import json
import time

class WirelessTurbineController(bpy.types.Operator):
    bl_idname = "wm.wireless_turbine_controller"
    bl_label = "ESP32 Wireless Turbine Controller"
    
    _timer = None
    last_time = 0.0
    current_angle = 0.0
    
    # ─── CONFIGURATION ───
    # Replace with the exact local IP printed by your ESP32 Serial Monitor
    esp32_ip = "10.1.1.181" 

    def modal(self, context, event):
        # Allow user to terminate the live link cleanly by pressing ESC in the viewport
        if event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            now = time.time()
            dt = now - self.last_time
            self.last_time = now

            try:
                # Poll the ESP32 JSON API with a strict network timeout to protect UI frame rate
                url = f"http://{self.esp32_ip}/status"
                response = urllib.request.urlopen(url, timeout=0.03)
                data = json.loads(response.read().decode())

                # Target the exact spinning node from your model script
                rotor_bearing = bpy.data.objects.get("Rotor_Spin_Bearing")
                
                if rotor_bearing:
                    # Clear the existing default driver expression so it doesn't fight the Wi-Fi data
                    if rotor_bearing.animation_data and rotor_bearing.animation_data.drivers:
                        rotor_bearing.driver_remove("rotation_euler", 2)

                    # Check if system is active on your phone dashboard
                    if data.get("running", 0) == 1:
                        target_rpm = data.get("rpm", 0)
                        
                        # Convert RPM to Rad/Sec (Angular Velocity)
                        # Speed factor scaled down slightly (0.10) for smoother high-RPM visual rendering
                        omega = ((target_rpm * 2.0 * 3.14159) / 60.0) * 0.10
                        
                        # Accumulate rotational displacement along the local Z-axis (Index 2)
                        self.current_angle -= omega * dt
                        rotor_bearing.rotation_euler[2] = self.current_angle
                        
                        # Force update the active viewport layer
                        context.view_layer.update()
                        
            except Exception:
                # Silently catch brief network drops or latency spikes to keep Blender stable
                pass

        return {'PASS_THROUGH'}

    def execute(self, context):
        self.last_time = time.time()
        wm = context.window_manager
        
        # Runs at roughly 60Hz loop rate to capture data changes smoothly
        self._timer = wm.event_timer_add(0.016, window=context.window)
        wm.modal_handler_add(self)
        print(">>> Wireless control link engaged with ESP32 turbine node.")
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        print(">>> Wireless control link terminated.")

def register():
    bpy.utils.register_class(WirelessTurbineController)

def unregister():
    bpy.utils.unregister_class(WirelessTurbineController)

if __name__ == "__main__":
    register()
    # Run the operator loop immediately upon execution
    bpy.ops.wm.wireless_turbine_controller()
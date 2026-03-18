import psutil

def get_system_health():
    """
    Returns real-time CPU usage, RAM usage, and CPU Temperature.
    Non-blocking and optimized for BMO v1.6.0.
    """
    try:
        # Get CPU usage (0.1s interval to ensure a fresh reading)
        cpu_usage = psutil.cpu_percent(interval=0.1)
        
        # Get RAM usage percentage
        ram_info = psutil.virtual_memory()
        
        # Get Temperature (checking most common Linux sensor nodes)
        cpu_temp = 0
        sensors = psutil.sensors_temperatures()
        
        # Priority list for CPU temperature sensors
        for label in ['k10temp', 'coretemp', 'cpu_thermal', 'package id 0']:
            if label in sensors:
                cpu_temp = sensors[label][0].current
                break
                
        return {
            "cpu_usage": int(cpu_usage),
            "ram_usage": int(ram_info.percent),
            "cpu_temp": int(cpu_temp)
        }
    except Exception:
        # Fallback to zero values to prevent BMO from crashing
        return {
            "cpu_usage": 0,
            "ram_usage": 0,
            "cpu_temp": 0
        }

if __name__ == "__main__":
    # Local test: run 'python src/modules/bmo_tools.py' to verify
    stats = get_system_health()
    print(f"--- BMO SENSORS CHECK ---")
    print(f"CPU: {stats['cpu_usage']}% | RAM: {stats['ram_usage']}% | TEMP: {stats['cpu_temp']}°C")

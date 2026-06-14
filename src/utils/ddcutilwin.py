import ctypes
from ctypes import wintypes

# --- 1. Define Necessary Windows Data Types and Structures ---
# High-Level Monitor Configuration API structures
class PHYSICAL_MONITOR(ctypes.Structure):
    _fields_ = [
        ('hPhysicalMonitor', wintypes.HANDLE),
        ('szPhysicalMonitorDescription', wintypes.WCHAR * 128)
    ]

# --- 2. Load the Required Windows DLLs ---
user32 = ctypes.windll.user32
dxva2 = ctypes.windll.dxva2

# --- 3. Get the Handle to the Monitor ---
# For simplicity, we grab the handle of the primary desktop window
hwnd = user32.GetDesktopWindow()
hMonitor = user32.MonitorFromWindow(hwnd, 1)  # 1 = MONITOR_DEFAULTTOPRIMARY

# --- 4. Get the Physical Monitor Handle ---
# First, we need to find out how many physical monitors are associated with that HMONITOR
num_monitors = wintypes.DWORD(0)
if not dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hMonitor, ctypes.byref(num_monitors)):
    raise RuntimeError("Failed to get number of physical monitors.")

if num_monitors.value == 0:
    raise RuntimeError("No physical monitors found.")

# Allocate an array of PHYSICAL_MONITOR structures based on the count
monitor_array = (PHYSICAL_MONITOR * num_monitors.value)()

# Populate the array with the actual physical monitor handles
if not dxva2.GetPhysicalMonitorsFromHMONITOR(hMonitor, num_monitors, monitor_array):
    raise RuntimeError("Failed to get physical monitor handles.")

# We will use the first physical monitor found
hPhysicalMonitor = monitor_array[0].hPhysicalMonitor

# --- 5. Call GetVCPFeature ---
# VCP Code 0x10 corresponds to Monitor Brightness
VCP_BRIGHTNESS = 0x10

# Variables to store the output values
current_value = wintypes.DWORD()
maximum_value = wintypes.DWORD()
vcp_code_type = wintypes.DWORD() # Usually returns the type (e.g., continuous vs non-continuous)

print(f"Querying VCP Code 0x10 (Brightness) for monitor: {monitor_array[0].szPhysicalMonitorDescription}")

# Call the function
# Low-level equivalent signature
# BOOL GetVCPFeatureAndVCPFeatureReply(HANDLE hMonitor, BYTE bVcpCode, LPMC_VCP_CODE_TYPE pvct, LPDWORD pdwCurrentValue, LPDWORD pdwMaximumValue);
success = ctypes.windll.dxva2.GetVCPFeatureAndVCPFeatureReply(
    hPhysicalMonitor,
    VCP_BRIGHTNESS,
    ctypes.byref(vcp_code_type),
    ctypes.byref(current_value),
    ctypes.byref(maximum_value)
)

if success:
    print("--- Success ---")
    print(f"Current Brightness Value: {current_value.value}")
    print(f"Maximum Brightness Value: {maximum_value.value}")
else:
    # If this fails, ensure your physical monitor has DDC/CI enabled in its OSD menu!
    print(f"Failed to get VCP feature. Windows Error Code: {ctypes.GetLastError()}")

# --- 6. Clean Up ---
# Always destroy the monitor handles when done to avoid memory leaks
dxva2.DestroyPhysicalMonitors(num_monitors, monitor_array)
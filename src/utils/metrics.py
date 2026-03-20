"""Controller of picframe."""

from datetime import datetime
import subprocess, psutil, platform


def get_cpu_temp(format="str"):
    try:
        output = subprocess.check_output(["vcgencmd", "measure_temp"], stderr=subprocess.STDOUT).decode('utf-8').strip().split("=")
        if len(output) > 1:
            if format == "str":
                return output[1].replace("'C", "°")
            else:
                return float(output[1].replace("'C", ""))
        else:
            return output[0]
    except Exception:
        return "--" if format == "str" else 0

def get_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def system_metrics():
    uname = platform.uname()
    cpu_load = [round(x / psutil.cpu_count() * 100, 1) for x in psutil.getloadavg()]
    cpufreq = psutil.cpu_freq()
    svmem = psutil.virtual_memory()
    partitions = psutil.disk_partitions()
    net_io = psutil.net_io_counters()
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    running_since = boot_time.strftime("%A %d. %B %Y")
    response =  f"System: `{uname.system}`\n"
    response += f"Node Name: `{uname.node}`\n"
    response += f"Release: `{uname.release}`\n"
    response += f"Version: `{uname.version}`\n"
    response += f"Machine: `{uname.machine}`\n\n"
    response += f"CPU Freq.: `{cpufreq.current}Mhz`\n"
    response += f"CPU cores: `{psutil.cpu_count(logical=False)}` vcores: `{psutil.cpu_count(logical=True)}`\n"
    response += f"CPU load: `{cpu_load}%`\n"
    response += f"CPU temp.: `{get_cpu_temp()}`\n"
    response += f"RAM size: `{get_size(svmem.total)}`\n"
    response += f"RAM used: `{get_size(svmem.used)}` (`{svmem.percent}%`)  free: `{get_size(svmem.free)}`\n\n"
    for partition in partitions:
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            continue
        response += f"{partition.device}\n"
        response += f"Size: `{get_size(partition_usage.total)}`\n"
        response += f"Used: `{get_size(partition_usage.used)}` (`{partition_usage.percent}%`)\n"
        response += f"Free: `{get_size(partition_usage.free)}`\n"
    response += f"\nTotal Bytes Sent: `{get_size(net_io.bytes_sent)}`\n"
    response += f"Total Bytes Received: `{get_size(net_io.bytes_recv)}`\n"
    response += f"Running since {running_since}"
    return response

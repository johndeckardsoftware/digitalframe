#
# Example of meteo station WiFi GW1100 dashboard
#
import requests, json, threading
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Force non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
from matplotlib.gridspec import GridSpec
import numpy as np
import datetime
from urllib.parse import quote
from plugin import PluginWrapper
from pyray import get_time, load_image, unload_texture, load_texture_from_image, unload_image, draw_texture
from utils.image import resize_to_percentage
from dftext import dftext

class WeatherPlugin(PluginWrapper):
    def __init__(self, digitalframe, config):
        super().__init__(digitalframe, config)
        self.active = False
        self.last_update = 0.0
        self.authorize = self.config.get('authorize', "test")
        self.device_id = self.config.get('device_id', "test")
        self.update_timeout = self.config.get('timeout', 5*60)
        self.mode = self.config.get('mode', "month")
        self.mode_list = ["day", "24h", "month", "year"]
        self.mode_index = -1
        self.dashboard = self.config.get('dashboard')
        self.zoom = self.config.get('zoom', 100)
        self.tint = self.config.get('tint', [255, 255, 255, 192])
        self.thread = None
        self.dashboard_texture = None

    def set_header(self, content_len):
        header = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-GB,en;q=0.9",
            "Connection": "keep-alive",
            "Content-Length": str(content_len),
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": "lang_var=en-us; ousaite_language=english; ousaite_unit_cookie_1=1; ousaite_unit_cookie_2=3; ousaite_unit_cookie_3=7; ousaite_unit_cookie_4=12; ousaite_unit_cookie_5=14; ousaite_unit_cookie_10=25; ousaite_unit_cookie_12=28; ousaite_unit_cookie_undefined=28; acw_tc=2ff62e9a17768847734943400eb0154c0d9051e60afafbfe86feffba77; cdn_sec_tc=2ff62e9a17768847734943400eb0154c0d9051e60afafbfe86feffba77",
            "Host": "www.ecowitt.net",
            "Origin": "https://www.ecowitt.net",
            "Referer": f"https://www.ecowitt.net/home/share?authorize={self.authorize}&device_id={self.device_id}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0",
        }
        return header

    def get_weather_info(self, mode):
        now = datetime.datetime.now()
        url = "https://www.ecowitt.net/index/get_data"
        if mode == "home": # day
            payload = f"device_id={self.device_id}&authorize={self.authorize}"
            url = "https://www.ecowitt.net/index/home"
        elif mode == "day":
            edate = quote(now.strftime("%Y-%m-%d 23:59"))
            sdate = quote(now.strftime("%Y-%m-%d 00:00"))
            payload=f"device_id={self.device_id}&is_list=0&mode=0&sdate={sdate}&edate={edate}&page=1&authorize={self.authorize}&sortList=1%7C3%7C4%7C5%7C6&hideList="
        elif mode == "24h":
            edate = int(now.timestamp())
            delta = now - datetime.timedelta(hours=24)
            sdate = int(delta.timestamp())
            payload=f"device_id={self.device_id}&is_list=0&mode=1&sdate={sdate}&edate={edate}&page=1&authorize={self.authorize}&sortList=1%7C3%7C4%7C5%7C6&hideList="
        elif mode == "month":
            edate = quote(now.strftime("%Y-%m-%d 23:59"))
            delta = now - datetime.timedelta(weeks=4)
            sdate = quote(delta.strftime("%Y-%m-%d 00:00"))
            payload=f"device_id={self.device_id}&is_list=0&mode=0&sdate={sdate}&edate={edate}&page=1&authorize={self.authorize}&sortList=1%7C3%7C4%7C5%7C6&hideList="
        else:
            edate = quote(now.strftime("%Y-%m-%d 23:59"))
            delta = now - datetime.timedelta(weeks=4)
            sdate = quote(delta.strftime("%Y-01-01 00:00"))
            payload=f"device_id={self.device_id}&is_list=0&mode=0&sdate={sdate}&edate={edate}&page=1&authorize={self.authorize}&sortList=1%7C3%7C4%7C5%7C6&hideList="
        header = self.set_header(len(payload))
        resp = requests.post(url, json=payload, headers=header)
        return resp.text

    def generate_plot(self, mode, json_input, output_file):
        # 1. Load the JSON data
        data = json.loads(json_input)

        # 2. Flatten the nested structure
        # This creates a single-row DataFrame where column names are the full JSON paths
        df_flat = pd.json_normalize(data['list'])

        # 3. Define the metrics to extract (Grouped by Subplot)
        metrics_groups = [
            {
                "title": "Thermodynamics",
                "ylabel": "Celsius (°C)",
                "lines": [
                    {'path': 'tempf.list.tempf', 'label': 'Temp', 'color': 'tab:red', 'style': '-'},
                    {'path': 'tempf.list.drew_temp', 'label': 'Dew Point', 'color': 'tab:blue', 'style': '--'}
                ]
            },
            {
                "title": "Moisture Analysis",
                "is_dual": True, # <--- Humidity on left, VPD on right
                "lines": [
                    {'path': 'humidity.list.humidity', 'label': 'Humidity (%)', 'color': 'tab:cyan'},
                    {'path': 'vpd.list.vpd', 'label': 'VPD (kPa)', 'color': 'tab:pink'}
                ]
            },
            {
                "title": "Wind Dynamics",
                "ylabel": "km/h",
                "lines": [
                    {'path': 'wind_speed.list.windspeedmph', 'label': 'Speed', 'color': 'tab:green'},
                    {'path': 'wind_speed.list.windgustmph', 'label': 'Gust', 'color': 'tab:orange', 'style': ':'}
                ]
            },
            {
                "title": "Atmospheric Pressure",
                "ylabel": "hPa",
                "lines": [{'path': 'pressure.list.baromrelin', 'label': 'Pressure', 'color': 'tab:purple'}]
            },
            {
                "title": "Solar & UV Index",
                "is_uv": True, # <--- Solar on left, UV on right
                "lines": [
                    {'path': 'so_uv.list.solarradiation', 'label': 'Solar (lx)', 'color': 'tab:orange'},
                    {'path': 'so_uv.list.uv', 'label': 'UV Index', 'color': 'brown'}
                ]
            },
            {
                "title": "Wind Direction",
                "ylabel": "Degrees (º)",
                "lines": [{'path': 'winddir.list.winddir', 'label': 'Direction', 'color': 'tab:gray', 'style': 'none', 'marker': '.'}]
            },
            {
                "title": "Precipitation",
                "ylabel": "mm",
                "lines": [{'path': 'rain.list.dailyrainin', 'label': 'Daily Rain', 'color': 'tab:blue'}]
            },
            {
                "title": "Precipitation",
                "ylabel": "mm",
                "lines": [{'path': 'rain_statistcs.list.monthlyrainin', 'label': 'Monthly Rain', 'color': "#2125EC"}],
            },
            {
                "title": "Precipitation",
                "ylabel": "mm",
                "lines": [{'path': 'rain_statistcs.list.yearlyrainin', 'label': 'Yearly Rain', 'color': "#031A99"}],
            },
        ]

        # 4. Construct a working DataFrame using the 'times' key as the index
        df = pd.DataFrame({'Timestamp': pd.to_datetime(data['times'])})

        # 5. Plotting all metrics in one dashboard
        fig, axes = plt.subplots(nrows=3, ncols=3, figsize=(24, 13.5), sharex=True)
        axes_flat = axes.flatten()

        for i, group in enumerate(metrics_groups):
            ax = axes_flat[i]

            if group.get("is_uv", False):
                # --- LEFT AXIS ---
                line1 = group['lines'][0]
                data1 = pd.to_numeric(df_flat[line1['path']].iloc[0], errors='coerce')
                ax.plot(df['Timestamp'], data1, color=line1['color'], label=line1['label'], lw=2)
                ax.set_ylabel(line1['label'], color=line1['color'], fontweight='bold')

                # --- RIGHT AXIS ---
                ax_right = ax.twinx()
                line2 = group['lines'][1]
                data2 = pd.to_numeric(df_flat[line2['path']].iloc[0], errors='coerce')
                # 1. Plot the UV line normally (Solid brown or black for clarity)
                ax_right.plot(df['Timestamp'], data2, color='black', lw=2, label='UV Index', zorder=5)

                # 2. Paint the "Risk Zones" in the background
                # This creates a vertical color scale that stays correct regardless of peaks/descents
                xlims = ax_right.get_xlim()
                ax_right.axhspan(0, 2, color='#289500', alpha=0.2, label='Low', zorder=1)       # Green
                ax_right.axhspan(2, 5, color='#F7E400', alpha=0.2, label='Moderate', zorder=1)  # Yellow
                ax_right.axhspan(5, 7, color='#F85900', alpha=0.2, label='High', zorder=1)      # Orange
                ax_right.axhspan(7, 10, color='#D8001D', alpha=0.2, label='V. High', zorder=1)  # Red
                ax_right.axhspan(10, 15, color='#6B49C8', alpha=0.2, label='Extreme', zorder=1) # Violet
                ax_right.set_ylim(0, max(11, np.nanmax(data2) + 1))
                ax_right.set_ylabel("UV Index", fontweight='bold')
                #ax_right.text(df['Timestamp'].iloc[0], 11.5, ' EXTREME', color='violet', fontsize=8, fontweight='bold', va='center')

                # Merge legends from both axes
                lines, labels = ax.get_legend_handles_labels()
                lines2, labels2 = ax_right.get_legend_handles_labels()
                ax.legend(lines + lines2, labels + labels2, loc='upper left', fontsize=8)

            elif group.get("is_dual", False):
                # --- LEFT AXIS ---
                line1 = group['lines'][0]
                data1 = pd.to_numeric(df_flat[line1['path']].iloc[0], errors='coerce')
                ax.plot(df['Timestamp'], data1, color=line1['color'], label=line1['label'], lw=2)
                ax.set_ylabel(line1['label'], color=line1['color'], fontweight='bold')

                # --- RIGHT AXIS ---
                ax_right = ax.twinx()
                line2 = group['lines'][1]
                data2 = pd.to_numeric(df_flat[line2['path']].iloc[0], errors='coerce')
                ax_right.plot(df['Timestamp'], data2, color=line2['color'], label=line2['label'], linestyle='--', lw=1.5)
                ax_right.set_ylabel(line2['label'], color=line2['color'], fontweight='bold')

                # Merge legends from both axes
                lines, labels = ax.get_legend_handles_labels()
                lines2, labels2 = ax_right.get_legend_handles_labels()
                ax.legend(lines + lines2, labels + labels2, loc='upper left', fontsize=8)

            else:
                # standard loop for grouped lines
                for line in group['lines']:
                    y_data = pd.to_numeric(df_flat[line['path']].iloc[0], errors='coerce')
                    ax.plot(df['Timestamp'], y_data, label=line['label'],
                            color=line['color'], linestyle=line.get('style', '-'),
                            marker=line.get('marker', None), lw=2)
                ax.set_ylabel(group.get('ylabel', ''), fontweight='bold')
                ax.legend(loc='upper left', fontsize=9)

            ax.set_title(group['title'], fontsize=16, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
            date_fmt = group.get("date_fmt", None)
            if date_fmt is None:
                if mode == "day" or mode == "24h": date_fmt = '%H-%M'
                else: date_fmt = '%m-%d'
            ax.xaxis.set_major_formatter(mdates.DateFormatter(date_fmt))
            plt.setp(ax.get_xticklabels(), rotation=30)

        plt.xlabel('Date/Time')
        plt.suptitle(f'{self.get_period(mode)} Weather Analytics', fontsize=18, fontweight='bold', y=0.99)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])

        # 6. Save the final rendering
        plt.savefig(output_file, dpi=160)

    def get_period(self, mode):
        if mode == "day": return "Daily"
        elif mode == "24h": return "24 Hours"
        elif mode == "month": return "Monthly"
        else: return "Yearly"

    def get_next_mode(self, inc):
        self.mode_index = (self.mode_index + inc) % len(self.mode_list)
        self.mode = self.mode_list[self.mode_index]
        return self.mode

    def update(self):
        if not self.active: return

        if self.last_update == 0.0 or self.update_timeout + self.last_update < get_time():
            self.last_update = get_time()
            if not self.thread:
                self.thread = threading.Thread(target=self.update_thread)
                self.thread.start()

    def update_thread(self):
        if self.authorize == "test":
            with open("src/resources/weather.json", "w") as file: weather_json = file.read()
        else:
            weather_json = self.get_weather_info(self.mode)
        self.generate_plot(self.mode, weather_json, self.dashboard)
        if self.dashboard_texture: self.dashboard_texture = unload_texture(self.dashboard_texture)
        self.thread = None

    def draw(self):
        if not self.active: return

        if self.thread:
            dftext(f"Weather is preparing the dashboard...", -3, 3, fs=-28, tint=(69,169,69,255), shadow=2)
            return

        if not self.dashboard_texture:
            dash = load_image(self.dashboard)
            resize_to_percentage(dash, self.df.width, self.df.height, self.zoom)
            if self.dashboard_texture: unload_texture(self.dashboard_texture)
            self.dashboard_texture = load_texture_from_image(dash)
            dash = unload_image(dash)

        draw_texture(self.dashboard_texture, (self.df.width - self.dashboard_texture.width) // 2, (self.df.height - self.dashboard_texture.height) // 2, self.tint)


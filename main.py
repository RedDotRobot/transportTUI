# Packages
# Textualize packages
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TabbedContent, TabPane, Select, Digits, Input, Button, LoadingIndicator
from rich.pretty import Pretty
from textual.containers import HorizontalGroup, VerticalGroup, Vertical, VerticalScroll, HorizontalScroll
from textual.reactive import reactive
from textual.binding import Binding

from textual_plotext import PlotextPlot

from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict

# Time
from datetime import datetime, date
import time

# File access
from dotenv import load_dotenv
import os
import json
import requests

from asciiart import *

# Load environment variables and prep https request
load_dotenv()
tfnswKey = os.getenv("TfNSW_KEY")
weatherKey = os.getenv("WEATHER_KEY")
headers: dict = {
        "Authorization": f"apiKey {tfnswKey}"
        }
stationList = json.load(open("stationList.json"))

def getGTFS(url: str, params: dict, headers: dict) -> str:

    response: requests.Response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    feedDict: dict = MessageToDict(feed, preserving_proto_field_name=True)

#    with open(f"responses/{time.time()}.json", "x") as f:
#        json.dump(feedDict, f, indent=2)

    return feed

class Clock(Digits):

    timeStr: reactive = reactive("")

    def on_mount(self) -> None:
        self.update_clock()
        self.set_interval(1/60, self.update_clock)

    def update_clock(self) -> None:
        timeNow: datetime = datetime.now()
        self.timeStr = timeNow.strftime("%H:%M:%S") # + f".{timeNow.microsecond // 1000:03}"

    def watch_timeStr(self, timeStr: str) -> None:
        self.update(timeStr)

class Alert(Static):

    def on_mount(self) -> None:

        url: str = "https://api.transport.nsw.gov.au/v2/gtfs/alerts/sydneytrains"
        params: dict = {
			"outputFormat": "rapidJSON",
			"coordOutputFormat": "EPSG:4326",
			"filterDateValid": date.today().strftime("%d-%m-%Y"),
			"filterPublicationStatus": "current"
		}

        data = getGTFS(url, params, headers)
        alerts = ["formatting this later because i'm lazy asf"]

        for entity in  data.entity:              # trust this works lmao
            if entity.HasField("alert"):
                alert = entity.alert
                # alerts.append(alert)

        self.update(Pretty(alerts))

class Trips(Static):

    def on_mount(self) -> None:

        url = "https://api.transport.nsw.gov.au/v2/gtfs/realtime/sydneytrains"
        tripData = getGTFS(url, "", headers)

        trips: list = []

        for entity in tripData.entity:
            trips.append(entity.id)

        self.update(Pretty(trips))

class CurrentWeather(VerticalGroup):

    lat, lon = "33.8688", "151.2093"
    location = "Sydney"

    currentWeatherData = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weatherKey}", params={"units": "metric"}).json()

    currentTemp = currentWeatherData["main"]["temp"]
    currentWeather = currentWeatherData["weather"][0]

    currentWeatherID = str(currentWeather["id"])

#    iconMap = {
#        "2": thunderstorm,
#        "3": drizzle,
#        "5": rain,
#        "6": snow,
#        "7": fog,
#        "800": clear,
#        "801": clear,
#        "802": partial_clouds,
#        "803": partial_clouds,
#        "804": clouds,
#    } 
#
#    if currentWeatherID[0] in ["2", "3", "5", "6", "7"]:
#        weatherIcon = iconMap.get(currentWeatherID[0], clear)
#    elif currentWeatherID[0] == "8":
#        weatherIcon = iconMap.get(currentWeatherID)
#    elif currentWeatherData["wind"]["speed"] >= 15:
#        weatherIcon = wind
#    else:
#        weatherIcon = clear

    def compose(self) -> ComposeResult:

        yield Digits(str(self.currentWeatherData["main"]["temp"]))
        # yield Static(f"↑{str(round(self.currentWeatherData["main"]["temp_max"], 1))} / ↓{str(round(self.currentWeatherData["main"]["temp_min"], 1))}", classes="bold")
        # yield Static(f"Feels like {str(round(self.currentWeatherData["main"]["feels_like"], 1))}")
        yield Static(Pretty(self.currentWeatherData))

class ForecastWeather(VerticalGroup):

    lat, lon = "33.8688", "151.2093"

    forecastWeatherData = requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={weatherKey}", params={"units": "metric"}).json()

    forecast = []
    timeList = []
    tempList = []

    for item in forecastWeatherData["list"]:

        timeList.append(item["dt"])
        tempList.append(item["main"]["temp"])

        forecast.append({
            "dt": item["dt"],
            "day": time.strftime("%d", time.gmtime(item["dt"])),
            "time": time.strftime("%H:%M", time.gmtime(item["dt"])),

            "temp": item["main"]["temp"],
            "temp_min": item["main"]["temp_min"],
            "temp_max": item["main"]["temp_max"],

            "weather": item["weather"],
            "cloudiness": item["clouds"]["all"],
            "wind": item["wind"],
            "pop": item["pop"],                 # probability of precipitation
            })

    class ForecastChart(PlotextPlot):           # another problem for another day frfr

        def on_mount(self) -> None:

            plt = self.plt
            plt.scatter(plt.sin())

    def compose(self) -> ComposeResult:

        forecast = Static(Pretty(self.forecast), classes="weather")
        forecast.border_title = "forecast"
        yield forecast

        forecastChart = self.ForecastChart()
        forecastChart.border_title = "chart"
        yield forecastChart

class transportTUI(App):

    CSS_PATH = "style.tcss"
    BINDINGS = [
            Binding(
                key="q",
                action="quit",
                description="Quit the app"
                ),
            Binding(
                key="1",
                action="show_tab('home')",
                description='Switch to main tab'
                ),
            Binding(
                key="2",
                action="show_tab('weather')",
                description='Switch to weather tab'
                ),
            Binding(
                key="3",
                action="show_tab('planner')",
                description='Switch to planning tab'
                ),
            ]

    def compose(self) -> ComposeResult:

        yield Header(name="transportTUI", icon="")

        with Vertical(id="sidebar"):
            yield Static()      # spacer
            clock: Digits = Clock()
            clock.border_title = "transportTUI"
            yield clock

            alert: Static = Alert()
            alert.border_title = "alerts"
            yield alert
        
            weather: VerticalGroup = CurrentWeather(classes="weather")
            weather.border_title = "weather"
            yield weather

        with TabbedContent(initial="home", classes="main"):
            with TabPane("home", id="home"):
                weather: VerticalGroup = CurrentWeather(classes="weather")
                weather.border_title = "weather"
                yield weather

            with TabPane("weather", id="weather"):
                yield ForecastWeather()

            with TabPane("planner", id="planner"):
                with HorizontalGroup():
                    yield Select.from_values(stationList, prompt="From", id="stationFrom", compact=True)
                    yield Select.from_values(stationList, prompt="To", id="stationTo", compact=True)
                    yield Button("Go", id="search")

                # yield Trips()

    # Change tab
    def action_show_tab(self, tab:str) -> None:
        self.get_child_by_type(TabbedContent).active = tab

if __name__ == "__main__":
    app = transportTUI(ansi_color=True)
    app.run()

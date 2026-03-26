import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Weather Dashboard",
                   page_icon="🌤", layout="wide")

# ── WMO weather code lookup ────────────────────────────────────────────────────
WMO_CODES = {
    0: ("Clear Sky", "☀️"),
    1: ("Mainly Clear", "🌤"), 2: ("Partly Cloudy", "⛅"), 3: ("Overcast", "☁️"),
    45: ("Fog", "🌫"), 48: ("Icy Fog", "🌫"),
    51: ("Light Drizzle", "🌦"), 53: ("Drizzle", "🌦"), 55: ("Heavy Drizzle", "🌧"),
    61: ("Light Rain", "🌧"), 63: ("Rain", "🌧"), 65: ("Heavy Rain", "🌧"),
    71: ("Light Snow", "🌨"), 73: ("Snow", "🌨"), 75: ("Heavy Snow", "❄️"),
    80: ("Rain Showers", "🌦"), 81: ("Heavy Showers", "🌧"), 82: ("Violent Showers", "⛈"),
    95: ("Thunderstorm", "⛈"), 96: ("Hail Storm", "⛈"), 99: ("Hail Storm", "⛈"),
}


def get_wmo(code):
    return WMO_CODES.get(code, ("Unknown", "🌡"))


def wind_dir_label(deg):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(deg / 45) % 8]

# ── API calls ──────────────────────────────────────────────────────────────────


def geocode(city):
    r = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 5, "language": "en", "format": "json"},
        timeout=8,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def fetch_weather(lat, lon):
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                       "wind_speed_10m,wind_direction_10m,precipitation,weathercode,uv_index",
            "hourly": "temperature_2m,precipitation_probability",
            "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "auto", "forecast_days": 7,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


# ── UI ─────────────────────────────────────────────────────────────────────────
st.title("🌤 Weather Dashboard")
st.caption("Powered by Open-Meteo • Free API • No key required")

city_input = st.text_input(
    "🔍 Search city", placeholder="e.g. Hyderabad, Tokyo, New York")
unit = st.radio("Temperature unit", ["°C", "°F"], horizontal=True)

if not city_input:
    st.info("Enter a city name above to get started.")
    st.stop()

with st.spinner("Finding location..."):
    try:
        results = geocode(city_input)
    except Exception as e:
        st.error(f"Geocoding failed: {e}")
        st.stop()

if not results:
    st.warning("No locations found. Try a different city name.")
    st.stop()

options = [
    f"{r['name']}, {r.get('admin1', '')}, {r['country']}" for r in results]
chosen_idx = st.selectbox("Select location", range(
    len(options)), format_func=lambda i: options[i])
loc = results[chosen_idx]

with st.spinner("Fetching weather..."):
    try:
        data = fetch_weather(loc["latitude"], loc["longitude"])
    except Exception as e:
        st.error(f"Weather fetch failed: {e}")
        st.stop()

cur = data["current"]
daily = data["daily"]
hourly = data["hourly"]


def fmt(c):
    return round(c * 9/5 + 32, 1) if unit == "°F" else c


# ── Current conditions ─────────────────────────────────────────────────────────
st.divider()
desc, icon = get_wmo(cur["weathercode"])
st.subheader(f"{icon} Current Conditions — {options[chosen_idx]}")
st.metric("Temperature", f"{fmt(cur['temperature_2m'])} {unit}",
          f"Feels like {fmt(cur['apparent_temperature'])} {unit}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("💧 Humidity",      f"{cur['relative_humidity_2m']} %")
c2.metric("💨 Wind",
          f"{cur['wind_speed_10m']} km/h {wind_dir_label(cur['wind_direction_10m'])}")
c3.metric("🌧 Precipitation", f"{cur['precipitation']} mm")
c4.metric("☀️ UV Index",      f"{cur['uv_index']}")
st.caption(f"Condition: {icon} {desc}")

# ── 7-day forecast ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("📅 7-Day Forecast")

cols = st.columns(7)
for i, col in enumerate(cols):
    day = datetime.strptime(daily["time"][i], "%Y-%m-%d")
    label = "Today" if i == 0 else day.strftime("%a %d")
    d_icon = get_wmo(daily["weathercode"][i])[1]
    hi = fmt(daily["temperature_2m_max"][i])
    lo = fmt(daily["temperature_2m_min"][i])
    rain = daily["precipitation_sum"][i]
    with col:
        st.markdown(f"**{label}**")
        st.write(d_icon)
        st.write(f"↑ {hi}{unit}")
        st.write(f"↓ {lo}{unit}")
        st.caption(f"🌧 {rain} mm")

# ── Hourly charts ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("⏱ 24-Hour Forecast")

hours = [datetime.strptime(h, "%Y-%m-%dT%H:%M").strftime("%H:%M")
         for h in hourly["time"][:24]]
temps = [fmt(t) for t in hourly["temperature_2m"][:24]]
rain_prob = hourly["precipitation_probability"][:24]

df = pd.DataFrame({
    f"Temperature ({unit})": temps,
    "Rain Probability (%)": rain_prob,
}, index=hours)

tab1, tab2 = st.tabs([f"🌡 Temperature ({unit})", "🌧 Rain Probability (%)"])
with tab1:
    st.line_chart(df[[f"Temperature ({unit})"]])
with tab2:
    st.bar_chart(df[["Rain Probability (%)"]])

st.caption("Data: [Open-Meteo](https://open-meteo.com/)")


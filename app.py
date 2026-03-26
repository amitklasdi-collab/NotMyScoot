import math
import random

import folium
import streamlit as st

st.set_page_config(page_title="NotMyScoot", layout="wide")

TEL_AVIV_CENTER: tuple[float, float] = (32.0853, 34.7818)

# Exact popup texts (required)
RED_POPUP = "🚨 Reported theft on March 10th. High risk zone."
YELLOW_POPUP = "⚠️ Poor lighting, no cameras. Exercise caution."
GREEN_POPUP = "✅ Secure parking with 24/7 CCTV and guards."
HOUSE_POPUP = (
    "🏠 Community Protection: Building guard at the entrance. Feel free to park right in front of the lobby."
)


def render_map(map_obj: folium.Map) -> None:
    # Crucial: always render via st_folium so the map is visible.
    from streamlit_folium import st_folium  # type: ignore

    st_folium(map_obj, width="100%", height=650)


def marker_div_icon(marker_color: str, size_px: int = 14, opacity: float = 0.95) -> folium.DivIcon:
    # DivIcon lets us render exact marker colors (including pure yellow).
    return folium.DivIcon(
        html=f"""
        <div style="
          width: {size_px}px; height: {size_px}px;
          background-color: {marker_color};
          opacity: {opacity};
          border-radius: 50%;
          border: 2px solid rgba(255,255,255,0.95);
          box-shadow: 0 6px 16px rgba(0,0,0,0.35);
        "></div>
        """
    )


def safe_haven_div_icon() -> folium.DivIcon:
    return folium.DivIcon(
        html="""
        <div style="
          width: 30px; height: 30px;
          background-color: #60a5fa;
          border-radius: 10px;
          border: 2px solid rgba(255,255,255,0.95);
          box-shadow: 0 8px 18px rgba(96,165,250,0.25);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 16px;
        ">🏠</div>
        """,
    )


def haversine_meters(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    h = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0) ** 2
    return 2.0 * r * math.asin(math.sqrt(h))


def point_within_radius(center: tuple[float, float], radius_meters: int, rng: random.Random) -> tuple[float, float]:
    lat, lon = center
    angle = rng.uniform(0.0, 2.0 * math.pi)
    r = radius_meters * math.sqrt(rng.random())

    meters_per_deg_lat = 111320.0
    meters_per_deg_lon = meters_per_deg_lat * math.cos(math.radians(lat))

    d_lat = (r * math.cos(angle)) / meters_per_deg_lat
    d_lon = (r * math.sin(angle)) / meters_per_deg_lon
    return (lat + d_lat, lon + d_lon)


def build_bounds(center: tuple[float, float], radius_meters: int) -> list[list[float]]:
    lat, lon = center
    lat_delta = radius_meters / 111320.0
    lon_delta = radius_meters / (111320.0 * math.cos(math.radians(lat)))
    south, north = lat - lat_delta, lat + lat_delta
    west, east = lon - lon_delta, lon + lon_delta
    return [[south, west], [north, east]]


def generate_theft_markers(
    center: tuple[float, float],
    radius_meters: int,
    rng: random.Random,
    count_range: tuple[int, int] = (5, 8),
) -> list[tuple[tuple[float, float], str, str]]:
    """
    Generates 5-8 markers of types red/yellow/green strictly inside the circle.
    Returns list of (location, popup_text, color_hex).
    """
    marker_specs = [
        ("red", RED_POPUP, "#ef4444"),
        ("yellow", YELLOW_POPUP, "#facc15"),
        ("green", GREEN_POPUP, "#22c55e"),
    ]

    count = rng.randint(count_range[0], count_range[1])
    results: list[tuple[tuple[float, float], str, str]] = []

    for _ in range(count):
        _name, popup_text, color_hex = rng.choice(marker_specs)

        # Rejection sampling to ensure strict inclusion in the circle.
        for _attempt in range(40):
            loc = point_within_radius(center, radius_meters, rng)
            if haversine_meters(center, loc) <= radius_meters:
                results.append((loc, popup_text, color_hex))
                break

    return results


def main() -> None:
    st.markdown("### 🛵🔒 NotMyScoot")

    # App state
    if "parking_mode" not in st.session_state:
        st.session_state["parking_mode"] = False
    if "menu_open" not in st.session_state:
        st.session_state["menu_open"] = False
    if "session_seed" not in st.session_state:
        st.session_state["session_seed"] = random.randint(1, 1_000_000)
    if "radius_meters" not in st.session_state:
        st.session_state["radius_meters"] = 100

    with st.sidebar:
        # Hamburger menu + actions
        if st.button("☰"):
            st.session_state["menu_open"] = not st.session_state["menu_open"]

        if st.session_state["menu_open"]:
            st.radio(
                "Menu",
                ["🚨 Report Theft", "🤝 Join Community", "🏠 Offer Safe Haven"],
                index=0,
                disabled=True,
            )

        if st.button("📍 I want to park here", use_container_width=True):
            st.session_state["parking_mode"] = True
            st.rerun()

        # Radius controls only in parking mode
        if st.session_state["parking_mode"]:
            radius = st.slider(
                "Radius (meters)",
                min_value=50,
                max_value=500,
                value=int(st.session_state["radius_meters"]),
                step=10,
            )
            st.session_state["radius_meters"] = int(radius)

            if st.button("Reset", use_container_width=True):
                st.session_state["parking_mode"] = False
                st.rerun()

    # Map
    user_location = TEL_AVIV_CENTER

    if not st.session_state["parking_mode"]:
        m = folium.Map(location=user_location, zoom_start=16, tiles="CartoDB positron")
        folium.Marker(
            location=user_location,
            popup="You are here",
            tooltip="You are here",
            icon=marker_div_icon("#3b82f6", size_px=18, opacity=1.0),
        ).add_to(m)

        # Safe Havens are visible even before parking mode
        for lat, lon in [(32.0842, 34.7812), (32.0876, 34.7882), (32.0817, 34.7724)]:
            folium.Marker(
                location=(lat, lon),
                popup=HOUSE_POPUP,
                tooltip=HOUSE_POPUP,
                icon=safe_haven_div_icon(),
            ).add_to(m)

        render_map(m)
        return

    radius_meters = int(st.session_state["radius_meters"])

    m = folium.Map(location=user_location, zoom_start=16, tiles="CartoDB positron")
    m.fit_bounds(build_bounds(user_location, radius_meters))

    # Circle around user location
    folium.Circle(
        location=user_location,
        radius=radius_meters,
        color="#2563eb",
        weight=2,
        fill=True,
        fill_color="#2563eb",
        fill_opacity=0.12,
    ).add_to(m)

    # User center marker
    folium.Marker(
        location=user_location,
        popup="You are here",
        tooltip="You are here",
        icon=marker_div_icon("#3b82f6", size_px=18, opacity=1.0),
    ).add_to(m)

    # Theft/safety markers inside circle only
    seed = int(st.session_state["session_seed"]) + radius_meters * 9973
    rng = random.Random(seed)
    theft_markers = generate_theft_markers(user_location, radius_meters, rng)

    for loc, popup_text, color_hex in theft_markers:
        folium.Marker(
            location=loc,
            popup=popup_text,
            tooltip=popup_text,
            icon=marker_div_icon(color_hex, size_px=14, opacity=0.95),
        ).add_to(m)

    # Safe Havens are always visible
    for lat, lon in [(32.0842, 34.7812), (32.0876, 34.7882), (32.0817, 34.7724)]:
        folium.Marker(
            location=(lat, lon),
            popup=HOUSE_POPUP,
            tooltip=HOUSE_POPUP,
            icon=safe_haven_div_icon(),
        ).add_to(m)

    render_map(m)


if __name__ == "__main__":
    main()


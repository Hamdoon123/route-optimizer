import streamlit as st
import os
import osmnx as ox
import networkx as nx
import folium
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(page_title="Delivery Route Optimizer", layout="wide")
st.title("🚚 Delivery Route Optimizer")

# User Inputs
with st.sidebar:
    st.header("Configuration")
    depot_lat = st.number_input("Depot Latitude", value=23.5850)
    depot_lon = st.number_input("Depot Longitude", value=58.3850)
    num_vehicles = st.slider("Number of Vehicles", 1, 5, 3)
    vehicle_capacity = st.number_input("Vehicle Capacity (kg per vehicle)", value=60)
    avg_speed = st.slider("Average Speed (km/h)", 20, 80, 40)

    st.markdown("---")
    st.subheader("Add Delivery Points")
    locations = []
    with st.form("add_locations"):
        lat = st.number_input("Latitude", key="lat")
        lon = st.number_input("Longitude", key="lon")
        weight = st.number_input("Package Weight (kg)", value=10.0)
        time_start = st.slider("Earliest Delivery Time (hr after 8am)", 0, 8, 2)
        time_end = st.slider("Latest Delivery Time (hr after 8am)", time_start + 1, 10, time_start + 2)
        submitted = st.form_submit_button("Add Delivery")
        if submitted:
            st.session_state.setdefault("deliveries", []).append((lat, lon, weight, (time_start * 60, time_end * 60)))

# Load road network
@st.cache_resource
def load_graph(lat, lon):
    return ox.graph_from_point((lat, lon), dist=25000, network_type='drive')

graph = load_graph(depot_lat, depot_lon)

# Process delivery points
if "deliveries" in st.session_state and st.session_state["deliveries"]:
    deliveries = st.session_state.deliveries
    node_ids = [ox.distance.nearest_nodes(G, lon, lat) for lat, lon, _, _ in deliveries]
    weights = [w for _, _, w, _ in deliveries]
    time_windows = [tw for _, _, _, tw in deliveries]

    assignments = [[] for _ in range(num_vehicles)]
    current_loads = [0] * num_vehicles

    for i, (node, w, tw) in enumerate(zip(node_ids, weights, time_windows)):
        for v in range(num_vehicles):
            if current_loads[v] + w <= vehicle_capacity:
                assignments[v].append((node, w, tw))
                current_loads[v] += w
                break

    colors = ['blue', 'green', 'red', 'orange', 'purple']
    m = folium.Map(location=(depot_lat, depot_lon), zoom_start=12)

    for v, stops in enumerate(assignments):
        if not stops:
            continue
        route_nodes = [depot_node] + [s[0] for s in stops] + [depot_node]
        route_coords = []
        for i in range(len(route_nodes) - 1):
            path = nx.shortest_path(G, route_nodes[i], route_nodes[i + 1], weight='length')
            coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in path]
            route_coords.extend(coords if i == 0 else coords[1:])
        folium.PolyLine(route_coords, color=colors[v % len(colors)], weight=5, opacity=0.8).add_to(m)
        for node, w, (start, end) in stops:
            y, x = G.nodes[node]['y'], G.nodes[node]['x']
            folium.Marker([y, x], tooltip=f"{w}kg | {start//60+8}:00–{end//60+8}:00").add_to(m)
    st.subheader("🚚 Optimized Delivery Map")
    st_data = st_folium(m, width=1000)
else:
    st.warning("Add delivery points in the sidebar to get started.")

import streamlit as st
import networkx as nx
import plotly.graph_objects as go
import math
from collections import deque

# --- Data Gedung Universitas
nodes = {
    "A": {"name": "Fakultas Teknik", "pos": (0, 0)},
    "B": {"name": "Fakultas Ekonomi", "pos": (1, 2)},
    "C": {"name": "Perpustakaan", "pos": (2, 1)},
    "D": {"name": "Gedung Rektorat", "pos": (3, 0)},
    "E": {"name": "Fakultas Ilmu Komputer", "pos": (4, 2)},
    "F": {"name": "Masjid Kampus", "pos": (5, 0)},
}

def euclidean(a, b):
    xa, ya = a
    xb, yb = b
    return math.hypot(xa - xb, ya - yb)

edges = []
keys = list(nodes.keys())
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        d = euclidean(nodes[keys[i]]["pos"], nodes[keys[j]]["pos"])
        if d < 3.5:  # threshold koneksi
            edges.append((keys[i], keys[j], d))

# --- Graph Initialization
G = nx.Graph()
for k, v in nodes.items():
    G.add_node(k, label=v["name"], pos=v["pos"])
G.add_weighted_edges_from(edges)

# --- Algoritma DFS
def dfs(graph, start, goal):
    visited = set()
    stack = [(start, [start])]
    while stack:
        node, path = stack.pop()
        if node == goal:
            return path
        if node not in visited:
            visited.add(node)
            for neighbor in sorted(graph.neighbors(node), reverse=True):
                if neighbor not in visited:
                    stack.append((neighbor, path + [neighbor]))
    return []

# --- Algoritma BFS
def bfs(graph, start, goal):
    visited = set()
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        if node == goal:
            return path
        if node not in visited:
            visited.add(node)
            for neighbor in sorted(graph.neighbors(node)):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))
    return []

# --- Algoritma Greedy Nearest Neighbor
def greedy(graph, start, goal):
    visited = set()
    path = [start]
    current = start
    while current != goal:
        visited.add(current)
        neighbors = list(graph.neighbors(current))
        min_dist = float("inf")
        next_node = None
        for neighbor in neighbors:
            if neighbor not in visited:
                dist = graph[current][neighbor]['weight']
                if dist < min_dist:
                    min_dist = dist
                    next_node = neighbor
        if next_node is None:
            return []  # tidak bisa mencapai goal
        path.append(next_node)
        current = next_node
    return path

# --- Visualisasi
def draw_graph(G, path=[]):
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = G.nodes[edge[0]]['pos']
        x1, y1 = G.nodes[edge[1]]['pos']
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    node_x, node_y = [], []
    node_labels = []
    for node in G.nodes():
        x, y = G.nodes[node]['pos']
        node_x.append(x)
        node_y.append(y)
        node_labels.append(G.nodes[node]['label'])

    fig = go.Figure()

    # Edges
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='gray'), mode='lines'))

    # Nodes
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode='markers+text',
        text=node_labels, textposition="bottom center",
        marker=dict(size=15, color='skyblue')))

    # Path highlight
    if path:
        path_x, path_y = [], []
        for i in range(len(path) - 1):
            x0, y0 = G.nodes[path[i]]['pos']
            x1, y1 = G.nodes[path[i+1]]['pos']
            path_x.extend([x0, x1, None])
            path_y.extend([y0, y1, None])
        fig.add_trace(go.Scatter(x=path_x, y=path_y, mode='lines', line=dict(width=4, color='red')))

    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
    return fig

# --- Streamlit UI
st.title("🏫 Kampus Navigator")
st.markdown("Cari rute terbaik antar gedung di kampus berdasarkan algoritma pilihanmu.")

options = list(nodes.keys())
start = st.selectbox("Pilih Gedung Awal", options, format_func=lambda x: nodes[x]["name"])
goal = st.selectbox("Pilih Gedung Tujuan", options, format_func=lambda x: nodes[x]["name"])
algo = st.selectbox("Pilih Algoritma", ["DFS", "BFS", "Greedy"])

if st.button("🔍 Temukan Rute"):
    if algo == "DFS":
        route = dfs(G, start, goal)
    elif algo == "BFS":
        route = bfs(G, start, goal)
    else:
        route = greedy(G, start, goal)

    if route:
        names = [nodes[r]["name"] for r in route]
        total = sum(G[route[i]][route[i+1]]['weight'] for i in range(len(route)-1))
        st.success(f"Rute ditemukan: {' → '.join(names)}")
        st.info(f"Total jarak: {total:.2f} unit")
        fig = draw_graph(G, path=route)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Rute tidak ditemukan.")
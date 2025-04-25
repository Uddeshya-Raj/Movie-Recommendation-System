## file to initialize recommender module
import os
from pytrie import StringTrie
from diskcache import Cache

cache = Cache("./cache")

api_key = "8265bd1679663a7ea12ac168da84d2e8"

# Open the file and read movie names into a list
current_dir = os.path.dirname(os.path.abspath(__file__))
movie_list_path = os.path.join(current_dir, "popular_movies.txt")

with open(movie_list_path, "r", encoding="utf-8") as file:
    movie_names = [line.strip() for line in file]

# if 'movie_names_trie' in cache:
#     movie_names = cache['movie_names_trie']
# else:
#     movie_names = StringTrie()
#     with open(movie_list_path, "r", encoding='utf-8') as file:
#         # movie_names = [line.strip() for line in file]
#         for line in file:
#             line = line.strip()
#             movie_names[line.lower()] = line
#     cache['movie_names_trie'] = movie_names

layout = {
    "name": "cose",          # Layout algorithm
    "idealEdgeLength": 100,  # Preferred edge length (pixels)
    "nodeOverlap": 30,       # Minimum node spacing (pixels)
    "refresh": 25,           # Layout refresh rate (iterations)
    "randomize": False,      # Initial random positioning
    "componentSpacing": 150, # Space between disconnected components
    "nodeRepulsion": 800000, # Node repulsion force
    "edgeElasticity": 200,   # Edge spring stiffness
    "nestingFactor": 8       # Compound node spacing
}   

stylesheet = [
    # Movie nodes
    {
        "selector": ".movie-node",
        "style": {
            "shape": "ellipse",
            "width": 200,
            "height": 200,
            "background-fit": "cover",
            "background-image": "data(image)",
            "background-color": "data(color)",
            "label": "",
            "font-size": "16px",
            "text-valign": "bottom",
            "text-halign": "center",
            "border-width": 3,
            "border-color": "data(color)"
        }
    },
    {
        "selector": ".movie-node:selected",
        "style": {
            "width": 250,
            "height": 250,
            "label": "data(label)",
            "font-size": "25px",
            "font-family": "Arial Black",
            "color": "white",
            "text-outline-color": "#222",
            "text-outline-width": 0.7,
            "text-valign": "bottom",
            "text-halign": "center"
        }
    },
    {
        "selector": ".movie-node:active",
        "style": {
            "width": 250,
            "height": 250,
            "overlay-opacity": 0,
            "label": "data(label)",
            "font-size": "25px",
            "font-family": "Arial Black",
            "color": "white",
            "text-outline-color": "#222",
            "text-outline-width": 0.7,
            "text-valign": "bottom",
            "text-halign": "center"
        }
    },
    # Person nodes
    {
        "selector": ".person-node",
        "style": {
            "shape": "ellipse",
            "width": 150,
            "height": 150,
            "background-fit": "cover",
            "background-image": "data(image)",
            "background-color": "data(color)",
            "label": "",
            "font-size": "16px",
            "text-valign": "bottom",
            "text-halign": "center",
            "border-width": 1,
            "border-color": "data(color)"
        }
    },
    {
        "selector": ".person-node:selected",
        "style": {
            "width": 200, 
            "height": 200,
            "label": "data(label)",
            "font-size": "25px",
            "font-family": "Arial Black",
            "color": "#fff",
            "text-outline-color": "#222",
            "text-outline-width": 0.7,
            "text-valign": "bottom",
            "text-halign": "center"
        }
    },
    {
        "selector": ".person-node:active",
        "style": {
            "width": 200, 
            "height": 200,
            "overlay-opacity": 0,
            "label": "data(label)",
            "font-size": "25px",
            "font-family": "Arial Black",
            "color": "#fff",
            "text-outline-color": "#222",
            "text-outline-width": 0.7,
            "text-valign": "bottom",
            "text-halign": "center"
        }
    },
    # Theme nodes
    {
        "selector": ".theme-node",
        "style": {
            "shape": "round-rectangle",
            "width": "data(width)",
            "height": 50,
            "background-color": "#e9f5e9",
            "background-opacity": 1,
            "label": "data(label)",
            "font-size": "20px",
            "font-weight": "bold",
            "text-valign": "center",
            "text-halign": "center",
            "border-width": 3,
            "border-color": "#a5d6a7",
        }
    },
    {
        "selector": ".theme-node:selected",
        "style": {
            "width": "data(expanded_width)",
            "height": 100,
            "label": "data(label)",
            "font-size": "25px",
            "font-family": "Arial Black",
            "color": "#fff",
            "text-outline-color": "#222",
            "text-outline-width": 0.7,
            "text-valign": "center",
            "text-halign": "center",
            "background-color": "#e9f5e9",
            'background-opacity': 1,
            "border-color": "#a5d6a7",
        }
    },
    {
        "selector": ".theme-node:active",
        "style": {
            "width": "data(expanded_width)",
            "height": 100,
            "overlay-opacity": 0,
            "label": "data(label)",
            "font-size": "25px",
            "font-family": "Arial Black",
            "color": "#fff",
            "text-outline-color": "#222",
            "text-outline-width": 0.4,
            "text-valign": "center",
            "text-halign": "center",
            "background-color": "#e9f5e9",
            'background-opacity': 1,
            "border-color": "#a5d6a7",
        }
    },
    # Edges
    {
        "selector": ".edge",
        "style": {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "line-color": "data(color)",
            "target-arrow-color": "data(color)",
            "width": 0.7,
            "label": "data(label)",
            "font-size": "20px",
            "transition-property": "width, line-color",
            "transition-duration": "0.3s"
        }
    },
    {
        "selector": ".edge:selected",
        "style": {
            "line-color": "#8B0000",
            "width": 2,
            "target-arrow-color": "#8B0000",
            "z-index": 9999,
            "font-size": "25px",
            "font-family": "Arial Black",
            "color": "grey",
            "text-outline-color": "#222",
            "text-outline-width": 0.7,
        }
    },
    
]   

# Export the list of movie names
__all__ = ["movie_names, api_key, layout, stylesheet"]
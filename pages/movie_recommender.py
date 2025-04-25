import streamlit as st
from streamlit_searchbox import st_searchbox
from recommender.data_loader import *
from recommender.utils import *
from recommender import movie_names
from st_cytoscape import cytoscape

# Load the model
@st.cache_resource
def load_model():
    return SentenceTransformer('paraphrase-MiniLM-L6-v2')
model = load_model()
st.title("Recommender")

# Session state
if 'dropdown_count' not in st.session_state:
    st.session_state.dropdown_count = 1
if 'selections' not in st.session_state:
    st.session_state.selections = [""] * 3
if 'submitted_movies' not in st.session_state:
    st.session_state.submitted_movies = []
# if 'selected_nodes' not in st.session_state:
#     st.session_state.selected_nodes = set()
# if 'selected_edges' not in st.session_state:
#     st.session_state.selected_edges = set()

# # Dummy movie options (can be replaced later)
# movie_options = ["The Shawshank Redemption", "The Godfather", "The Dark Knight",
#                 "Pulp Fiction", "Forrest Gump", "Inception", "Fight Club",]

movie_options = movie_names

# Function to add dropdown
def add_dropdown():
    if st.session_state.dropdown_count < 3:
        st.session_state.dropdown_count += 1

# def search_function(query: str) -> list:
#     """
#     Search for movies based on the query.
#     """
#     return movie_names.values(prefix=query.lower())[:10]

# Input section
with st.container():
    for i in range(st.session_state.dropdown_count):

        st.session_state.selections[i] = st.selectbox(
            f"Select Movie {i + 1}",
            options=[""] + movie_options,
            index=0,
            key=f"movie_select_{i}"
        )

        # st.session_state.selections[i] = st_searchbox(
        #     search_function=search_function,
        #     placeholder=f"Search Movie {i + 1}",
        #     # options=movie_options,
        #     key=f"movie_search_{i}",
        #     default=None,
        #     clear_on_submit=False
        # )

    col1, col2 = st.columns(2)
    with col1:
        st.button("Add", on_click=add_dropdown, disabled=st.session_state.dropdown_count >= 3)
    with col2:
        if st.button("Submit"):
            selected = [m for m in st.session_state.selections[:st.session_state.dropdown_count] if m]
            st.session_state.submitted_movies = selected

# Result section
if st.session_state.submitted_movies:
    st.markdown("---")
    st.subheader("Recommended Movies:")

    # Display movies in a row
    submitted_movies = st.session_state.submitted_movies
    ref_ids = [get_movie_id(movie_name=movie_name) for movie_name in submitted_movies]
    cand_ids = get_movie_pool(ref_ids)
    recommended_movies = find_similar_movies(cand_ids, ref_ids)


    cols = st.columns(len(recommended_movies))
    
    for idx, mov_id in enumerate(recommended_movies):
        movie_data = get_movie_data(movie_id=mov_id)
        if movie_data:
            poster_url = get_movie_poster(movie_data)
            movie_name = movie_data.get('title', 'Unknown')
            tmdb_url = f"https://www.themoviedb.org/movie/{mov_id}"
            with cols[idx]:
                if poster_url:
                    st.image(poster_url, use_container_width=True)
                else:
                    st.write("No image")
                # st.markdown(f"**{movie_data.get('title', 'Unknown')}**")
                st.markdown(
                    f'<a href="{tmdb_url}" target="_blank" style="text-decoration: none;"><b>{movie_name}</b></a>',
                    unsafe_allow_html=True
                )
        else:
            with cols[idx]:
                st.write(f"Movie not found: {movie_name}")

    st.markdown("---")
    st.subheader("Why watch these?")

    movies = []
    people = []
    themes = []
    # elements = []
    movie_nodes = []
    person_nodes = []
    theme_nodes = []
    edges = []


    for mov_id in ref_ids+recommended_movies:
        movie_data = get_movie_data(movie_id=mov_id)
        if movie_data:
            data = {
                'id': "mov_"+str(movie_data['id']),
                'mov_id': movie_data['id'],
                'title': movie_data['title'],
                'themes': get_combined_keywords(movie_data['id']),
                'poster_path': f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}",
                'overview': movie_data['overview'],
                'people': get_movie_credits(movie_data['id'])
            }
            movies.append(data)
    
    peeps = []
    for i in range(len(movies)):
        for j in range(i + 1, len(movies)):
            if (movies[i]['mov_id'] not in ref_ids or movies[j]['mov_id'] not in recommended_movies):
                continue
            mov1_peeps = movies[i]['people']
            mov2_peeps = movies[j]['people']
            
            ids1 = set(mov1_peeps['Actors'] + mov1_peeps['Directors'] + mov1_peeps['Writers'])
            ids2 = set(mov2_peeps['Actors'] + mov2_peeps['Directors'] + mov2_peeps['Writers'])
            common_ids = ids1.intersection(ids2)
            peeps.extend(common_ids)

            mov1_themes = movies[i]['themes'] ## reference movie themes
            mov2_themes = movies[j]['themes'] ## recommended movie themes
            common_themes = find_similar_keywords(mov1_themes, mov2_themes, threshold=0.7)
            themes.extend(common_themes)

    peeps = list(set(peeps))
    themes = list(set(themes))
    themes = group_similar_keywords(themes)
    for theme_grp in themes:
        theme_grp.sort(key=lambda x: len(x))

    # print("peeps:\n",peeps)
    for pid in peeps:
        person_data = id_to_person(person_id=pid)
        profession = None
        _ = person_data['known_for_department'] if person_data else None
        if _:
            if _ == 'Acting':
                profession = 'Actor'
            elif _ == 'Directing':
                profession = 'Director'
            elif _ == 'Writing':
                profession = 'Writer'
            else:
                profession = 'crew'
        if person_data:
            data = {
                'id': "per_"+str(person_data['id']),
                'pid': person_data['id'],
                'name': person_data['name'],
                'image_path': f"https://image.tmdb.org/t/p/w500{person_data['profile_path']}",
                'profession': profession
            }
            people.append(data)
    # print("people:\n",people)
    for movie in movies:
        # print(movie['poster_path'])
        movie_nodes.append({
            "data":{
                "id": movie['id'],
                "label": movie['title'],
                # "title": movie['title'],
                "type": "movie",
                "image": get_image_data_url(movie['poster_path']),
                "color": "#ff0000" if movie['mov_id'] in ref_ids else "#00ff00",
            },
            "classes": "movie-node"
        })

    for person in people:
        # print(person['image_path'])
        person_nodes.append({
            "data":{
                "id": person['id'],
                "label": person['name'],
                # "title": person['name'],
                "type": "person",
                "image": get_image_data_url(person['image_path']),
                "color": "#0000ff"
            },
            "classes": "person-node"
        })

    for i, theme_grp in enumerate(themes):
        theme_nodes.append({
            "data":{
                "id": f"theme_{i}",
                "label": theme_grp[0],
                "type": "theme",
                "color": "#98FF98",
                "width": str(len(theme_grp[0])*20) + "px",
                "expanded_width": str(len(theme_grp[0]) *25) + "px",
                # "border-color": "#a5d6a7",
            },
            "classes": "theme-node"
        })
    
    for mov in movies:
        for peeps in people:
            # print(peeps['id']," : ",peeps['name']," : ", peeps['profession'])
            proff_key = peeps['profession']+'s'
            if peeps['pid'] in mov['people'][proff_key]:
                edges.append({
                    "data":{
                        "id": f"{mov['id']}_{peeps['id']}",
                        "source": mov['id'],
                        "target": peeps['id'],
                        "label": peeps['profession'],
                        "color": "black"
                    },
                    "classes": "edge" 
                })
        for t_idx, theme_grp in enumerate(themes):
            k_list1 = theme_grp
            k_list2 = mov['themes']
            
            embeddings1 = get_embeddings(k_list1)
            embeddings2 = get_embeddings(k_list2)
            similarity_matrix = cosine_similarity(embeddings1, embeddings2)
            edge = False
            for i in range(len(k_list1)):
                for j in range(len(k_list2)):
                    if similarity_matrix[i][j] > 0.7:
                        edges.append({
                            "data":{
                                "id": f"{mov['id']}_theme_{t_idx}",
                                "source": mov['id'],
                                "target": f"theme_{t_idx}",
                                "label": '',
                                "color": "black"
                            },
                            "classes": "edge" 
                        })
                        edge = True
                        break
                if edge:
                    break

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
    
    st.markdown(
        """
        <style>
         div.element-container:has(iframe)  {
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 10px;
            box-shadow: 0 0 8px rgba(0, 0, 0, 0.05);
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

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

    cyto_return = cytoscape(
        elements=movie_nodes + person_nodes + theme_nodes + edges,
        layout=layout,
        stylesheet=stylesheet,
        height="750px",
        width="100%",
        key="cytoscape-graph"
    )

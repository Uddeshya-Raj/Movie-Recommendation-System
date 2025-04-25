import streamlit as st
from streamlit_searchbox import st_searchbox
from recommender.data_loader import *
from recommender.utils import *
from recommender import movie_names
from st_cytoscape import cytoscape
from recommender import stylesheet, layout

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
if 'profile' not in st.session_state:
    st.session_state.profile = defaultdict(int)
if "used_movies" not in st.session_state:
    st.session_state.used_movies = set()

movie_options = movie_names

# Function to add dropdown
def add_dropdown():
    if st.session_state.dropdown_count < 3:
        st.session_state.dropdown_count += 1

def update_profile(movie_id, action):
    if movie_id in st.session_state.used_movies:
        return
    else:
        st.session_state.used_movies.add(movie_id)
    genres = get_movie_genre(movie_id=movie_id)
    if action == "add":
        for genre in genres:
            st.session_state.profile[genre] += 1
    elif action == "remove":
        for genre in genres:
            st.session_state.profile[genre] -= 1
            if st.session_state.profile[genre] < 0:
                st.session_state.profile[genre] = 0

def create_movie_element(movie_id):
    data = get_movie_data(movie_id=movie_id)
    if not data:
        return None
    col = st.columns(1)[0]
    with st.container(border=True):
        poster_url =  f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
        st.image(poster_url, use_container_width=True)
        st.markdown(f"**{data['title']}**")

        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            st.button(
                "➕",
                key=f"add_{movie_id}",
                on_click=update_profile,
                args=(movie_id, "add"),
                help="you liked this movie",
                use_container_width=True,
                disabled=movie_id in st.session_state.used_movies
            )
        with col2:
            st.button(
                "➖",
                key=f"remove_{movie_id}",
                on_click=update_profile,
                args=(movie_id, "remove"),
                help="you disliked this movie",
                use_container_width=True,
                disabled=movie_id in st.session_state.used_movies
            )

# Input section
with st.container():
    for i in range(st.session_state.dropdown_count):

        st.session_state.selections[i] = st.selectbox(
            f"Select Movie {i + 1}",
            options=[""] + movie_options,
            index=0,
            key=f"movie_select_{i}"
        )

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

    submitted_movies = st.session_state.submitted_movies
    ref_ids = [get_movie_id(movie_name=movie_name) for movie_name in submitted_movies]
    cand_ids = get_movie_pool(ref_ids)
    pool = sorted(cand_ids, key=lambda mov_id: get_movie_goodness_score(mov_id), reverse=True)
    recommended_movies = find_similar_movies(cand_ids, ref_ids)
    pool = [movie_id for movie_id in pool if movie_id not in recommended_movies]

    movies = []
    people = []
    themes = []
    movie_nodes = []
    person_nodes = []
    theme_nodes = []
    edges = []

    # create initial profile
    for movie_id in ref_ids:
        genres = get_movie_genre(movie_id=movie_id)
        for genre in genres:
            st.session_state.profile[genre] += 1

    # generate graph data
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

    tab1, tab2 = st.tabs(["Movie Recommendations", "User Profile"])
    with tab1:
        st.subheader("Recommended Movies:")

        # Display movies in a row
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

        cyto_return = cytoscape(
            elements=movie_nodes + person_nodes + theme_nodes + edges,
            layout=layout,
            stylesheet=stylesheet,
            height="750px",
            width="100%",
            key="cytoscape-graph"
        )

    with tab2:
        st.subheader("Genre Preference Profile:")
        st.write("Your profile is based on the movies you liked/disliked.")
        
        total_score = sum(st.session_state.profile.values())
        if total_score > 0:
            percentage_profile = {genre: (score / total_score) * 100 for genre, score in st.session_state.profile.items()}
        else:
            percentage_profile = {genre: 0 for genre in st.session_state.profile.keys()}

        chart_data = {
            'Genre': list(percentage_profile.keys()),
            'Strength': list(percentage_profile.values())
        }

        st.bar_chart(chart_data, x='Genre', y='Strength')

        st.subheader("Movie Recommendations:") 
        st.write("Tell us which movies you liked/disliked to improve your recommendations.")

        with st.container(height=600, border=True):
            pool_cols = st.columns(5)
            for idx, mov_id in enumerate(recommended_movies+pool):
                with pool_cols[idx % 5]:
                    create_movie_element(mov_id)


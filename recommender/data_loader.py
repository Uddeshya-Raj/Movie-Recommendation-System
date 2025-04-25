import requests
import urllib.parse
import concurrent.futures
from typing import List, Dict, Optional, Any
import time
import math
import json
from diskcache import Cache
from SPARQLWrapper import SPARQLWrapper, JSON
import streamlit as st
from recommender import api_key

cache = Cache('./cache') 

def clear_cache():
    """Clear the cache"""
    cache.clear()

def remove_cache(key):
    """Remove a specific key from the cache"""
    if key in cache:
        cache.delete(key)

@st.cache_data
def get_movie_id(movie_name):
    url = "https://api.themoviedb.org/3/search/movie?api_key=" + api_key + "&query=" + urllib.parse.quote(movie_name)
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        movies = [m for m in data["results"] if m["title"].lower() == movie_name.lower()]
        if(len(movies)):
            movies.sort(key=lambda x: x["popularity"], reverse=True)
            return movies[0]["id"]
        else:
            return None
    else:
        return None

@st.cache_data    
def get_movie_data(movie_name=None, movie_id=None):
    params_dict = {
        'movie_name': movie_name,
        'movie_id': movie_id,
    }
    filtered_params = {k: v for k, v in params_dict.items() if v is not None}
    cache_key = f"get_movie_data:{json.dumps(filtered_params, sort_keys=True)}"

    if cache_key in cache:
        return cache[cache_key]

    if movie_id:  # Fetch by movie ID
        movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}"
    elif movie_name:  # Fetch by movie name
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={urllib.parse.quote(movie_name)}"
        search_response = requests.get(search_url, timeout=10)
        if search_response.status_code == 200:
            movies = [m for m in search_response.json()['results'] if m['title'].lower() == movie_name.lower()]
            if not movies:
                return None
            movies.sort(key=lambda x: x['popularity'], reverse=True)
            movie_url = f"https://api.themoviedb.org/3/movie/{movies[0]['id']}?api_key={api_key}"
        else:
            return None
    else:
        return None  # If neither movie_name nor movie_id is provided

    response = requests.get(movie_url)
    response_json = response.json() if response.status_code == 200 else None
    if response_json:
        cache.set(cache_key, response_json, expire=86400)
    return response_json

@st.cache_data
def get_movie_poster(movie_data):
    if not movie_data or 'poster_path' not in movie_data:
        return None
    poster_path = movie_data['poster_path']
    return f"https://image.tmdb.org/t/p/w500{poster_path}"

def get_movie_genre(movie_id, genre_id = False, session=None):
    url = "https://api.themoviedb.org/3/movie/" + str(movie_id) + "?api_key=" + api_key
    req = session if session else requests
    response = req.get(url)
    if response.status_code == 200:
        data = response.json()["genres"]
        if genre_id:
            gerere_id_list = [genre["id"] for genre in data]
            return gerere_id_list
        else:
            gerere_name_list = [genre["name"] for genre in data]
            return gerere_name_list
    else:
        return None
    
def genre_id_to_name(genre_id):
    url = "https://api.themoviedb.org/3/genre/movie/list?api_key=" + api_key
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()["genres"]
        gerere_name_list = [genre["name"] for genre in data if genre["id"] in genre_id]
        return gerere_name_list
    else:
        return None
    
def get_movie_keywords(movie_id):
    url = "https://api.themoviedb.org/3/movie/" + str(movie_id) + "/keywords?api_key=" + api_key
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()["keywords"]
        keywords = [keyword["name"] for keyword in data]
        return keywords
    else:
        return None

def get_movie_credits(movie_id, session=None):

    cache_key = f"credits:{movie_id}"
    if cache_key in cache:
        return cache[cache_key]
    
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={api_key}"
    req = session if session else requests
    response = req.get(url)
    
    if response.status_code == 200:
        data = response.json()
        directors = [crew['id'] for crew in data['crew'] if crew['job'] == 'Director'][:3]
        writers = [crew['id'] for crew in data['crew'] if crew['job'] in ['Writer', 'Screenplay']][:3]
        actors = [actor['id'] for actor in data['cast'][:5]]


        people = {
            "Directors": directors,
            "Writers": writers,
            "Actors": actors,
            "crews": [] # empty list requierd to avoid errors due to unhandeled keys
        }
        cache.set(cache_key, people, expire=86400)
        return people
    
    return None

@st.cache_data
def id_to_person(person_id):
    cache_key = f"person:{person_id}"
    if cache_key in cache:
        return cache[cache_key]
    
    url = f"https://api.themoviedb.org/3/person/{person_id}?api_key={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        cache.set(cache_key, data, expire=86400)
        return data
    
    return None

def find_related_movies(movie_id, session=None):
    req = session if session else requests
    movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}"
    recommendations_url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations?api_key={api_key}&sort_by=popularity.desc"
    movie_response = req.get(movie_url)
    recommendations_response = req.get(recommendations_url)

    if movie_response.status_code == 200:
        movie_data = movie_response.json()
        collection = movie_data.get('belongs_to_collection')

        if collection:  # If movie belongs to a collection
            collection_id = collection['id']
            collection_url = f"https://api.themoviedb.org/3/collection/{collection_id}?api_key={api_key}"
            collection_response = requests.get(collection_url)
            if collection_response.status_code == 200:
                collection_movies = [m for m in collection_response.json().get('parts', [])]
                collection_movies = sorted(collection_movies, key=lambda x: x['popularity'], reverse=True)
                collection_movies = [cm['id'] for cm in collection_movies if cm['id'] != movie_id][:5]
            else:
                collection_movies = []
        else:
            collection_movies = []

    if recommendations_response.status_code == 200:
        recommendations = [m['id'] for m in recommendations_response.json().get('results', [])][:5]
    else:
        recommendations = []
    
    related_movies = list(set(collection_movies + recommendations))
    return related_movies

@st.cache_data
def get_movie_goodness_score(movie_id: int) -> float:
    """
    Calculate goodness score for a movie based on its popularity and vote_average and vote_count.

    Args:
        movie_id: TMDB movie ID
    
    Returns:
        Goodness score (float)
    """
    movie_data = get_movie_data(movie_id=movie_id)
    if not movie_data:
        return 0.0

    # Extract relevant fields
    popularity = movie_data.get('popularity', 0.0)
    vote_average = movie_data.get('vote_average', 0.0)
    vote_count = movie_data.get('vote_count', 0)

    # Normalize vote_count to avoid division by zero
    if vote_count == 0:
        vote_count = 1

    # Calculate goodness score
    greatness_score = vote_average * math.log10(vote_count)
    goodness_score = (0.4*popularity) + (0.6*greatness_score)
    return goodness_score
    
@st.cache_data
def search_movies(actor_id=None, director_id=None, writer_id=None, genre_id=None, limit=15):
    """
    Search for movies based on actor, director, writer, or genre.
    Results are cached to avoid redundant API calls.
    """
    # Create a unique cache key based on function parameters
    params_dict = {
        'actor_id': actor_id,
        'director_id': director_id,
        'writer_id': writer_id,
        'genre_id': genre_id,
        'limit': limit,
    }
    cache_key = f"search_movies:{json.dumps(params_dict, sort_keys=True)}"

    # Check if the result is already cached
    if cache_key in cache:
        return cache[cache_key]

    # If not cached, make the API call
    url = "https://api.themoviedb.org/3/discover/movie?api_key=" + api_key
    params = {}

    if actor_id:
        params['with_cast'] = actor_id
    if director_id or writer_id:
        params['with_crew'] = ','.join(filter(None, [str(director_id), str(writer_id)]))
    if genre_id:
        params['with_genres'] = genre_id
    params['sort_by'] = 'popularity.desc'

    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        results = [movie['id'] for movie in response.json().get("results", [])[:limit]]
        
        # Cache the results with a TTL of 24 hours (86400 seconds)
        cache.set(cache_key, results, expire=86400)
        
        return results

    return None

def get_movie_pool(movie_ids: List[int]) -> List[int]:
    # start_time = time.time()
    similar_movies = set()
    
    # Create a session for connection pooling
    session = requests.Session()
    
    # Function to get all data for a single movie (NO CACHING HERE)
    def get_movie_all_data(movie_id: int) -> Dict:
        results = {}
        results['genres'] = get_movie_genre(movie_id, genre_id=True, session=session)
        results['related'] = find_related_movies(movie_id, session=session)
        results['credits'] = get_movie_credits(movie_id, session=session)
        return results

    # print("Data fetching for reference movies started after", time.time()-start_time)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:  # Reduced workers
        futures = [executor.submit(get_movie_all_data, mid) for mid in movie_ids]
        all_data = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # print("Data fetching for reference movies finished after", time.time()-start_time)
    
    # Process the collected data
    genres = set()
    directors = set()
    writers = set()
    actors = set()
    
    for data in all_data:
        genres.update(data['genres'] or [])
        similar_movies.update(data['related'] or [])
        if data['credits']:
            directors.update(data['credits'].get("Directors", []))
            writers.update(data['credits'].get("Writers", []))
            actors.update(data['credits'].get("Actors", []))
    
    # print("Searching for similar movies started after", time.time()-start_time)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        search_tasks = []
        def _submit_search(**kwargs):
            return executor.submit(search_movies, **kwargs)

        for genre in genres:
            search_tasks.append(_submit_search(genre_id=genre, limit=15))

        for director in directors:
            search_tasks.append(_submit_search(director_id=director, limit=5))

        for writer in writers:
            search_tasks.append(_submit_search(writer_id=writer, limit=5))
        
        for actor in actors:
            search_tasks.append(_submit_search(actor_id=actor, limit=5))
        
    
        # Collect results
        for task in concurrent.futures.as_completed(search_tasks):
            result = task.result()
            if result:
                similar_movies.update(result)
    
    # print("Searching for similar movies finished after", time.time()-start_time)
    
    # Remove original movies
    similar_movies -= set(movie_ids)
    
    return list(similar_movies)


@st.cache_data
def get_combined_keywords(movie_id: int, api_key: str=api_key) -> list:
    """Returns combined keywords from TMDB and Wikidata with optimizations"""
    # Cache keys
    cache_key_tmdb = f"keywords:tmdb:{movie_id}"
    cache_key_wiki = f"keywords:wiki:{movie_id}"
    movie_name = get_movie_data(movie_id=movie_id).get("original_title", None)
    # Try TMDB cache first
    tmdb_keywords = cache.get(cache_key_tmdb, default=None)
    # if(tmdb_keywords is not None):
        # print("TMDB cache hit")
        # print(f"TMDB keywords: {tmdb_keywords}")
    if tmdb_keywords is None:
        # print("TMDB cache miss")
        try:
            tmdb_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&append_to_response=keywords"
            with requests.Session() as session:
                response = session.get(tmdb_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    tmdb_keywords = [k["name"] for k in data.get("keywords", {}).get("keywords", [])]
                    # Cache even empty results to prevent API hammering
                    cache.set(cache_key_tmdb, tmdb_keywords, expire=3600)
                    # print("stored in cache. ",f"TMDB keywords: {cache_key_tmdb} : {tmdb_keywords}")
        except requests.exceptions.RequestException as e:
            print(f"TMDB API Error: {str(e)}")
            return None

    # Try Wikidata cache next
    wikidata_props = cache.get(cache_key_wiki, default=None)
    # if(wikidata_props is not None):
        # print("Wikidata cache hit")
        # print(f"Wikidata keywords: {wikidata_props}")
    
    if wikidata_props is None:
        # print("Wikidata cache miss")
        sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        sparql.addCustomHttpHeader("User-Agent", "MovieRecommenderProject/1.0 (uddeshya24@iitk.ac.in)")
        query = f"""
        SELECT DISTINCT ?propertyLabel WHERE {{
          ?film wdt:P4947 "{movie_id}";
                (wdt:P136|wdt:P921) ?property.
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        
        wikidata_props = []
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                sparql.setQuery(query)
                sparql.setReturnFormat(JSON)
                results = sparql.query().convert()
                wikidata_props = [result["propertyLabel"]["value"] 
                                for result in results["results"]["bindings"]]
                # Cache even empty results
                cache.set(cache_key_wiki, wikidata_props, expire=3600)
                # print("stored in cache. ",f"Wikidata keywords: {cache_key_wiki} : {wikidata_props}")
                break
            except Exception as e:
                if '429' in str(e) and attempt < max_retries:
                    time.sleep(1 + attempt)
                    continue
                print(f"Wikidata Error: ({movie_name}) {str(e)}")
                break

    # Clean Wikidata keywords (applied even to cached results)
    def clean_keyword(kw: str) -> str:
        return ' '.join(
            word for word in kw.split() 
            if word.lower() != 'film' and not (word == 'Film' and '-' not in kw)
        ).strip()

    wikidata_props = [clean_keyword(kw) for kw in (wikidata_props or [])]
    wikidata_props = [kw for kw in wikidata_props if kw]

    # Merge results (handle None cases)
    tmdb_keywords = tmdb_keywords or []
    wikidata_props = wikidata_props or []
    
    return list(set(tmdb_keywords + wikidata_props))

    

def get_wikidata_fallback(title: str, year: str) -> list:
    """Fallback query using title/year"""
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    query = f"""
    SELECT DISTINCT ?propertyLabel WHERE {{
      ?film wdt:P31 wd:Q11424;
            rdfs:label "{title}"@en;
            wdt:P577 ?date.
      FILTER(YEAR(?date) = {year})
      {{ ?film wdt:P136 ?property }}
      UNION
      {{ ?film wdt:P921 ?property }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    try:
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)  # Add this line to fix format
        results = sparql.query().convert()
        
        # Handle empty results safely
        if 'results' not in results:
            return []
            
        return [
            result["propertyLabel"]["value"]
            for result in results["results"]["bindings"]
            if "propertyLabel" in result
        ]
    except Exception as e:
        print(f"Fallback query failed: {str(e)}")
        return []

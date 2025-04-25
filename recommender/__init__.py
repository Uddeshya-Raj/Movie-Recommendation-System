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
        

# Export the list of movie names
__all__ = ["movie_names, api_key"]
from recommender.data_loader import *
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Tuple
import numpy as np
import base64
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

img_cache = Cache('./img_cache')

model = SentenceTransformer('paraphrase-MiniLM-L6-v2')  # 22M parameters

def clear_img_cache():
    """Clear image cache"""
    img_cache.clear()

def theme_similarity(keywords_a: list, keywords_b: list) -> float:
    """Compare keyword sets using semantic embeddings"""
    # Convert keywords to sentence-like format
    theme_a = ", ".join(sorted(keywords_a)[:-1])
    theme_a = theme_a+ " and " + keywords_a[-1] if len(keywords_a) > 1 else theme_a
    theme_b = ", ".join(sorted(keywords_b)[:-1])
    theme_b = theme_b+ " and " + keywords_b[-1] if len(keywords_b) > 1 else theme_b
    
    # Generate embeddings
    embeddings = model.encode([theme_a, theme_b])
    
    return cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

# @st.cache_data
def get_embeddings(texts: List[str]) -> np.ndarray:
    texts = [t.strip().lower() for t in texts]  # Normalize
    embeddings = [None] * len(texts)
    to_encode = []
    encode_indices = []

    # Step 1: Check cache for each keyword
    for i, text in enumerate(texts):
        key = "emb_" + text
        if key in cache:
            embeddings[i] = cache[key]
        else:
            to_encode.append(text)
            encode_indices.append(i)

    # Step 2: Encode missing ones in a batch
    if to_encode:
        encoded = model.encode(to_encode, convert_to_tensor=False)  # returns np.ndarray
        for i, text in enumerate(to_encode):
            key = "emb_" + text
            cache[key] = encoded[i]
            embeddings[encode_indices[i]] = encoded[i]

    return np.array(embeddings)

# @st.cache_data
def find_similar_keywords(keywords_a: List[str], 
                         keywords_b: List[str], 
                         threshold: float = 0.7) -> List[str]:
    """
    Find semantically similar keyword pairs between two lists
    
    Args:
        keywords_a: reference movie's keywords from get_combined_keywords()
        keywords_b: candidate movie's keywords from get_combined_keywords()
        threshold: Similarity cutoff (0.7 works well for most cases)
    
    Returns:
        List of (keyword_a, keyword_b, similarity_score) tuples
    """
    # Get cached embeddings for both lists
    embeddings_a = get_embeddings(keywords_a)
    embeddings_b = get_embeddings(keywords_b)
    
    # Calculate all pairwise similarities
    similarity_matrix = cosine_similarity(embeddings_a, embeddings_b)
    
    # Find pairs above threshold
    similar_pairs = []
    for i in range(len(keywords_a)):
        for j in range(len(keywords_b)):
            score = similarity_matrix[i][j]
            if score >= threshold:
                similar_pairs.append((keywords_a[i], keywords_b[j], float(score)))
    
    # Sort by descending similarity
    similar_pairs = sorted(similar_pairs, key=lambda x: -x[2])
    # return similar_pairs
    themes =  list(set(pair[0] for pair in similar_pairs))
    if len(themes) == 0:
        return []
    theme_embeddings = get_embeddings(themes)
    similarity_matrix = cosine_similarity(theme_embeddings, theme_embeddings)
    similar_themes = []
    for i in range(len(themes)):
        for j in range(i + 1, len(themes)):
            score = similarity_matrix[i][j]
            if score >= 0.8:
                similar_themes.append((themes[i], themes[j], float(score)))
    similar_themes = sorted(similar_themes, key=lambda x: -x[2])
    # return similar_themes

    # Group themes into clusters based on similar themes

    theme_groups = []
    visited = set()

    # Create adjacency list for similar themes
    adjacency_list = defaultdict(list)
    for theme_a, theme_b, _ in similar_themes:
        adjacency_list[theme_a].append(theme_b)
        adjacency_list[theme_b].append(theme_a)

    # Perform DFS to group similar themes
    def dfs(theme, group):
        visited.add(theme)
        group.append(theme)
        for neighbor in adjacency_list[theme]:
            if neighbor not in visited:
                dfs(neighbor, group)

    for theme in themes:
        if theme not in visited:
            group = []
            dfs(theme, group)
            theme_groups.append(group)

    return [theme[0] for theme in theme_groups]

# @st.cache_data
def group_similar_keywords(keywords: List[str], threshold: float = 0.7) -> List[List[str]]:
    """
    Groups keywords based on semantic similarity using paraphrase-MiniLM-L6-v2 model.
    
    Args:
        keywords: List of keywords/phrases to group
        threshold: Similarity score cutoff (0-1)
        
    Returns:
        List of lists where each sublist contains similar keywords
    """
    
    # Generate embeddings for all keywords
    embeddings = model.encode(keywords, convert_to_tensor=True)
    
    # Calculate pairwise similarity matrix
    similarity_matrix = cosine_similarity(embeddings)
    
    # Group similar keywords
    groups = []
    visited = set()
    
    for i, keyword in enumerate(keywords):
        if i not in visited:
            # Start new group with current keyword
            group = [keyword]
            visited.add(i)
            
            # Find similar unvisited keywords
            for j in range(len(keywords)):
                if j not in visited and similarity_matrix[i][j] >= threshold:
                    group.append(keywords[j])
                    visited.add(j)
            
            groups.append(group)
    
    return groups

def get_keywords_sentence(keywords):
    """Convert keyword list to natural language string"""
    if not keywords:
        return ""
    theme_a = ", ".join(sorted(keywords)[:-1])
    theme_a = theme_a+ " and " + keywords[-1] if len(keywords) > 1 else theme_a
    return theme_a


def final_movie_list(results: List[List[Tuple[int, float]]])-> List[int]:
    """
    Create final movie list based on the results from find_similar_movies
    
    Args:
        results: Output from find_similar_movies()
        
    Returns:
        Final list of movie IDs
    """
    final_list = set()
    remaining_list = []
    for movie_group in results:
        movie_group_ = [(movie_id, get_movie_goodness_score(movie_id)) for movie_id, _ in movie_group]
        # movie_group_.sort(key=lambda x: x[1], reverse=True)
        final_list.add(movie_group_[0][0])
        remaining_list.extend(movie_group_[1:])
    remaining_list.sort(key=lambda x: x[1], reverse=True)
    while(len(final_list) < 5 and len(remaining_list) > 0):
        movie_id, _ = remaining_list.pop(0)
        final_list.add(movie_id) 
    return list(final_list)
            

def find_similar_movies(candidates, references):
    """
    For each reference movie in references, find top 6 candidates from candidates
    with most similar keywords
    
    Args:
        candidates: Candidate movie IDs (search pool)
        references: Reference movie IDs (3 master movies)
        api_key: TMDB API key
        
    Returns:
        List of 3 lists, each containing (candidate_id, similarity_score) tuples
    """
    # Fetch all keywords in parallel
    all_ids = candidates + references
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_combined_keywords, mid, api_key): mid 
                  for mid in all_ids}
        keyword_map = {}
        for future in futures:
            mid = futures[future]
            keyword_map[mid] = future.result() or []

    # Prepare reference and candidate data
    references = [(rid, get_keywords_sentence(keyword_map[rid])) for rid in references]
    candidates = [(cid, get_keywords_sentence(keyword_map[cid])) for cid in candidates]

    # Batch encode all text
    ref_texts = [r[1] for r in references]
    cand_texts = [c[1] for c in candidates]
    
    ref_embeddings = model.encode(ref_texts)
    cand_embeddings = model.encode(cand_texts)

    # Compute similarity matrix (refs x candidates)
    similarity_matrix = cosine_similarity(ref_embeddings, cand_embeddings)

    # Get top 6 candidates for each reference
    results = []
    candidate_ids = [c[0] for c in candidates]
    
    for ref_idx in range(len(references)):
        scores = similarity_matrix[ref_idx]
        ranked = sorted(zip(candidate_ids, scores), 
                       key=lambda x: x[1], 
                       reverse=True)[:10]
        results.append([(cid, float(score)) for cid, score in ranked])

    # Ensure minimum 5 unique movies
    all_candidates = {cid for sublist in results for cid, _ in sublist}
    
    if len(all_candidates) < 5:
        needed = 5 - len(all_candidates)
        for ref_idx in range(len(results)):
            current = results[ref_idx]
            existing = {cid for cid, _ in current}
            
            # Find replacement candidates not already selected
            replacement_pool = [(cid, score) 
                               for cid, score in zip(candidate_ids, similarity_matrix[ref_idx])
                               if cid not in all_candidates]
            
            for i in range(len(current)):
                if needed <= 0:
                    break
                if current[i][0] in existing and replacement_pool:
                    new_cid, new_score = replacement_pool.pop(0)
                    current[i] = (new_cid, float(new_score))
                    all_candidates.add(new_cid)
                    needed -= 1

    return final_movie_list(results)

@img_cache.memoize(expire=86400)
def get_image_data_url(url: str) -> str:
    """Fetch image and return as Base64 data URL"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode("utf-8")
            return f"data:{response.headers['Content-Type']};base64,{b64}"
        return ""
    except Exception as e:
        print(f"Image fetch error: {str(e)}")
        return ""
    


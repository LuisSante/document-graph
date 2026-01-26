from sentence_transformers import SentenceTransformer, util
from collections import Counter

import json
import re
import os
import logging

logger = logging.getLogger(__name__)

def create_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

def read_txt(path_txt):
    with open(path_txt, 'r', encoding='utf-8') as f:
        txt = f.read()
    return txt

def write_json(path_struct_graph, final_json):
    with open(path_struct_graph, 'w', encoding='utf-8') as f:
        json.dump(final_json, f, indent=4)

    return final_json

def is_lower(sentences):
    char = sentences[0]
    if char.islower():
        return True
    return False

def is_number_page(ssentences):
    if len(ssentences) <= 2:
        if ssentences.isdigit():
            return True
    return False

def isHeader_or_isFooter(text):
    paragraphs = [p for p in text.split('\n') if p.strip() != '']
    paragraphs = [p for p in paragraphs if is_number_page(p) == False]

    paragraph_counts = Counter(paragraphs)
    
    repeated_paragraphs = [
        paragraph 
        for paragraph, count in paragraph_counts.items() 
        if count > 2
    ]
    
    return repeated_paragraphs

def isInit_paragraph_page(header_footer, sentences, text):
    for i in range(len(text)):
        if (sentences in text[i]) and (text[i-1] in header_footer) and (is_number_page(text[i-2]) == True):
            return True
    return False

def isParagraph_curt(header_footer, sentences, text):
    for i in range(len(text)):
        if (isInit_paragraph_page(header_footer, sentences, text) and (text[i-3][0] != text[i])):
            return True
    return False

def create_nodes(text):
    header_footer = isHeader_or_isFooter(text)
    paragraphs = [p for p in text.split('\n') if p.strip() != '']

    for p in range(len(paragraphs)):
        if p >= 3:
            if isParagraph_curt(header_footer, paragraphs[p], paragraphs):
                paragraphs[p-3] = paragraphs[p-3] + ' ' + paragraphs[p]
                paragraphs[p] = ''
            elif is_lower(paragraphs[p]):
                paragraphs[p-3] = paragraphs[p-3] + ' ' + paragraphs[p]
                paragraphs[p] = ''

    paragraphs = [p for p in paragraphs if is_number_page(p) == False]
    paragraphs = [p for p in paragraphs if p != '']

    return paragraphs


def generate_graph_data(paragraphs: list) -> dict:
    # BELLICUMPHARMACEUTICALS,INC_05_07_2019-EX-10.1-Supply Agreement
    model = SentenceTransformer('all-MiniLM-L6-v2')

    ## EXPLAIN WHY ?
    nodes = []
    edges = []
    
    for p in paragraphs:
        nodes.append({
            "id": p.id,
            "documentId": p.documentId,
            "text": p.text.strip(),
            "paragraph_enum": p.paragraph_enum,
            "page": p.page,
            "bbox": p.bbox,
            "relationsCount": p.relationsCount
        })
    
    logger.info(f"TOTAL PARAGRAPH {len(paragraphs)}\n\n")
    logger.info(f"TOTAL NODES {len(nodes)}\n\n")

    for i in range(len(nodes)):      
        #text = "See Section 3.2.1 for details"
        
        # Hierarchical pattern: captures sections with sublevels
        ref_match = re.search(r'[Ss]ection\s+(\d+(\.\d+)*)', nodes[i]["text"])        
        # ref_match.group(1) -> "3.2.1"

        # Simple pattern: only captures the main number
        # ref_match = re.search(r'[Ss]ection\s+(\d+)', nodes[i]["text"])
        # ref_match.group(1) -> "3"

        if ref_match:
            section_num = ref_match.group(1)
            for target_node in nodes:
                if target_node["text"].strip().startswith(f"{section_num}"):
                    edges.append({
                            "source": nodes[i]["id"], 
                            "target": target_node["id"], 
                            "type": "reference"
                    })

    if nodes:
        embeddings = model.encode([n["text"] for n in nodes], convert_to_tensor=True)
        cosine_scores = util.cos_sim(embeddings, embeddings)

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                if cosine_scores[i][j] > 0.8: # Threshold for similarity
                    edges.append({
                        "source": nodes[i]["id"], 
                        "target": nodes[j]["id"], 
                        "type": "semantic_similarity", 
                        "score": float(cosine_scores[i][j])
                    })

    relations_map = {}
    for edge in edges:
        s, t = edge['source'], edge['target']
        relations_map[s] = relations_map.get(s, 0) + 1
        relations_map[t] = relations_map.get(t, 0) + 1
    
    for node in nodes:
        node["relationsCount"] = relations_map.get(node["id"], 0)

    return {"nodes": nodes, "edges": edges}

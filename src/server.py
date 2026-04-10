from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

app = Flask(__name__)

# vector index
model = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.IndexFlatL2(384)
data_store = [] 

def add_entry(src, trg, text, trans):
    # Vectorize and add to faiss index
    emb = model.encode([text]).astype('float32')
    index.add(emb)
    
    # Save for RAG
    data_store.append({
        "source_language": src,
        "target_language": trg,
        "sentence": text,
        "translation": trans
    })

def create_prompt(src, trg, query, k=4):
    if not data_store:
        return f"Translate {src} to {trg}:\n{query}"

    # Search top k similar examples 
    q_emb = model.encode([query]).astype('float32')
    _, ids = index.search(q_emb, min(k, len(data_store)))
    
    #  prompt context
    shots = ""
    for i in ids[0]:
        if i == -1: continue
        item = data_store[i]
        # language pair 
        if item['source_language'] == src and item['target_language'] == trg:
            shots += f"Source: {item['sentence']} -> Translation: {item['translation']}\n"

    return f"Translate from {src} to {trg}.\n\nExamples:\n{shots}\nQuery: {query}\nTranslation:"

#API Endpoints 

@app.route('/pairs', methods=['POST'])
def post_pair():
    # Receive new translation pair 
    data = request.json
    add_entry(
        data['source_language'], 
        data['target_language'], 
        data['sentence'], 
        data['translation']
    )
    return "ok" # Required output 

@app.route('/prompt', methods=['GET'])
def get_prompt():
    # Generate RAG prompt 
    src = request.args.get('source_language')
    trg = request.args.get('target_language')
    query = request.args.get('query_sentence')
    
    prompt = create_prompt(src, trg, query)
    return jsonify({"prompt": prompt}) 

@app.route('/stammering', methods=['GET'])
def check_stammer():
    # Advanced: Detect repetition 
    trans = request.args.get('translated_sentence', '')
    words = trans.lower().split()
    
    # Logic: Flag if a word repeats 3+ times or is unnaturally long 
    has_stammer = False
    for i in range(len(words) - 2):
        if words[i] == words[i+1] == words[i+2]:
            has_stammer = True
            break
            
    if any(len(w) > 40 for w in words):
        has_stammer = True

    return jsonify({"has_stammer": has_stammer}) 

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=8000)

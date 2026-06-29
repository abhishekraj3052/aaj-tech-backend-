import os
import re
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from utils.greetings import GREETINGS_MAP


# Lazy load the embedding model to keep startup instant
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        # 90MB local sentence transformer model (very fast)
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model

# Local storage configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "chromadb_store")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "catalogs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DB_PATH, exist_ok=True)

# Lazy load ChromaDB client
_chroma_client = None

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=DB_PATH)
    return _chroma_client

def get_collection():
    client = get_chroma_client()
    try:
        return client.get_or_create_collection(name="aaj_tech_rag")
    except Exception as e:
        print(f"RAG: Collection access error ({e}). Recreating collection...")
        try:
            client.delete_collection(name="aaj_tech_rag")
        except Exception:
            pass
        return client.get_or_create_collection(name="aaj_tech_rag")

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Normalize whitespaces
    return re.sub(r'\s+', ' ', text).strip()

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    text = clean_text(text)
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

class RagEngine:
    @staticmethod
    def extract_pdf_text(pdf_path: str) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            return ""

    @staticmethod
    def index_data(db) -> int:
        """Loads products, categories, blogs, and local PDFs, chunks them, generates embeddings and indexes into ChromaDB."""
        collection = get_collection()
        
        # Clear existing collections
        client = get_chroma_client()
        try:
            client.delete_collection(name="aaj_tech_rag")
        except Exception:
            pass
        
        collection = get_collection()
        embed_model = get_embedding_model()
        
        documents = []
        metadatas = []
        ids = []
        chunk_count = 0

        # Helper to queue chunks
        def add_chunks(text: str, meta: Dict[str, Any], doc_id_prefix: str):
            nonlocal chunk_count
            text_chunks = chunk_text(text)
            for idx, chunk in enumerate(text_chunks):
                documents.append(chunk)
                metadatas.append({**meta, "chunk_index": idx})
                ids.append(f"{doc_id_prefix}_chunk_{chunk_count}")
                chunk_count += 1

        print("RAG: Fetching MongoDB Products...")
        # 1. Standard Products
        for prod in db.products.find():
            specs_str = ", ".join([f"{k}: {v}" for k, v in prod.get("specifications", {}).items() if v])
            features_str = ", ".join(prod.get("features", []))
            
            prod_text = f"Product: {prod.get('name')}. "
            if prod.get("sku"):
                prod_text += f"SKU: {prod.get('sku')}. "
            if prod.get("description"):
                prod_text += f"Description: {prod.get('description')}. "
            if features_str:
                prod_text += f"Features: {features_str}. "
            if specs_str:
                prod_text += f"Specifications: {specs_str}. "
                
            meta = {
                "source": "product",
                "id": str(prod["_id"]),
                "name": prod.get("name"),
                "sku": prod.get("sku", ""),
                "type": "standard",
                "link": f"/products/{str(prod['_id'])}"
            }
            add_chunks(prod_text, meta, f"prod_{str(prod['_id'])}")

        # 2. EV Products
        print("RAG: Fetching MongoDB EV Products...")
        for prod in db.ev_products.find():
            variants_str = ", ".join(prod.get("variants", []))
            ev_text = f"EV Product: {prod.get('title')}. "
            if prod.get("applications"):
                ev_text += f"Applications: {prod.get('applications')}. "
            if prod.get("details"):
                ev_text += f"Details: {prod.get('details')}. "
            if variants_str:
                ev_text += f"Variants: {variants_str}. "
                
            meta = {
                "source": "ev_product",
                "id": str(prod["_id"]),
                "name": prod.get("title"),
                "sku": "",
                "type": "ev",
                "link": "/ev-products"
            }
            add_chunks(ev_text, meta, f"ev_{str(prod['_id'])}")

        # 3. Wire Harness Products
        print("RAG: Fetching MongoDB Harness Products...")
        for prod in db.harness_products.find():
            variants_str = ", ".join(prod.get("variants", []))
            harness_text = f"Harness Product: {prod.get('title')}. "
            if prod.get("applications"):
                harness_text += f"Applications: {prod.get('applications')}. "
            if prod.get("details"):
                harness_text += f"Details: {prod.get('details')}. "
            if variants_str:
                harness_text += f"Variants: {variants_str}. "
                
            meta = {
                "source": "harness_product",
                "id": str(prod["_id"]),
                "name": prod.get("title"),
                "sku": "",
                "type": "harness",
                "link": "/wire-harness-products"
            }
            add_chunks(harness_text, meta, f"harness_{str(prod['_id'])}")

        # 4. Categories
        print("RAG: Fetching MongoDB Categories...")
        for cat in db.categories.find():
            cat_text = f"Product Category: {cat.get('name')}. Description: {cat.get('description', '')}."
            meta = {
                "source": "category",
                "id": str(cat["_id"]),
                "name": cat.get("name"),
                "sku": "",
                "type": "category",
                "link": "/products"
            }
            add_chunks(cat_text, meta, f"cat_{str(cat['_id'])}")

        # 5. Blogs
        print("RAG: Fetching MongoDB Blogs...")
        for blog in db.blogs.find():
            blog_text = f"Blog Title: {blog.get('title')}. Excerpt: {blog.get('excerpt')}. Content: {blog.get('content')}."
            meta = {
                "source": "blog",
                "id": str(blog["_id"]),
                "name": blog.get("title"),
                "sku": "",
                "type": "blog",
                "link": f"/blog/{str(blog['_id'])}"
            }
            add_chunks(blog_text, meta, f"blog_{str(blog['_id'])}")

        # 6. Uploaded Local PDFs
        print("RAG: Processing local catalog PDFs...")
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                if filename.endswith(".pdf"):
                    pdf_path = os.path.join(UPLOAD_DIR, filename)
                    pdf_text = RagEngine.extract_pdf_text(pdf_path)
                    if pdf_text.strip():
                        # Calculate and update chunk count in MongoDB
                        try:
                            chunks = chunk_text(pdf_text)
                            db.chatbot_documents.update_one(
                                {"filename": filename},
                                {"$set": {"chunkCount": len(chunks)}},
                                upsert=True
                            )
                        except Exception as e:
                            print(f"Error saving PDF chunkCount: {e}")
                            
                        meta = {
                            "source": "pdf",
                            "id": filename,
                            "name": filename,
                            "sku": "",
                            "type": "pdf",
                            "link": f"/api/catalog/download/{filename}"
                        }
                        add_chunks(pdf_text, meta, f"pdf_{filename.replace('.', '_')}")

        # Bulk write to ChromaDB
        if documents:
            print(f"RAG: Bulk indexing {len(documents)} text chunks into ChromaDB...")
            embeddings = []
            for i in range(0, len(documents), 100):
                batch_docs = documents[i:i+100]
                batch_embeds = embed_model.encode(batch_docs).tolist()
                embeddings.extend(batch_embeds)
                
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            print("RAG: Indexing complete.")
        
        return chunk_count

    @staticmethod
    def classify_intent(query: str) -> str:
        query_clean = query.strip().lower()
        query_clean_no_punct = re.sub(r'[^\w\s]', '', query_clean)
        
        # Product detection helper
        product_terms = [
            "power connector", "connector", "sb50", "sb75", "terminal block",
            "wire harness", "cable assembly", "heat shrink sleeve", "mc4",
            "xt60", "xt90", "rj45", "idc", "wire", "harness", "cable",
            "terminal", "sleeve"
        ]
        
        contains_product = False
        for pt in product_terms:
            if pt in query_clean_no_punct or f" {pt} " in f" {query_clean_no_punct} ":
                contains_product = True
                break
                
        # 1. Quote Request triggers
        quote_triggers = ["need quotation", "send quote", "pricing", "price", "cost", "quotation", "rates", "price list"]
        if any(qt in query_clean_no_punct for qt in quote_triggers):
            return "QUOTE_REQUEST"
            
        # 2. Contact triggers
        contact_triggers = ["contact number", "phone number", "email address", "sales contact", "call me", "contact", "phone", "email"]
        if any(ct in query_clean_no_punct for ct in contact_triggers):
            return "CONTACT"
            
        # 3. Shipping triggers
        shipping_triggers = ["delivery available", "shipping charges", "dispatch time", "courier service", "delivery", "shipping", "dispatch", "courier"]
        if any(st in query_clean_no_punct for st in shipping_triggers):
            return "SHIPPING"
            
        # 4. FAQ triggers - only if it does NOT contain any product names
        if not contains_product:
            faq_triggers = ["office timing", "office location", "gst number", "who are you", "about company", "payment methods", "where are you located", "gst", "payment", "timing", "hours", "located", "location", "address"]
            if any(ft in query_clean_no_punct for ft in faq_triggers):
                return "FAQ"
                
        # 5. Product info triggers
        info_triggers = ["what is", "tell me about", "explain", "features", "uses", "details", "specifications", "applications", "where is"]
        if any(it in query_clean_no_punct for it in info_triggers):
            return "PRODUCT_INFO"
            
        # 6. Product search triggers
        if contains_product:
            return "PRODUCT_SEARCH"
            
        return "GENERAL"
    @staticmethod
    def answer_query(query: str, db) -> Dict[str, Any]:
        query_clean = re.sub(r'[^\w\s]', '', query.strip().lower())
        
        product_count = 0
        faq_count = 0
        
        # Check if the query is an exact category name click/query
        try:
            exact_category = db.categories.find_one({"name": {"$regex": f"^{re.escape(query.strip())}$", "$options": "i"}})
            if exact_category:
                cat_id_str = str(exact_category["_id"])
                prods = list(db.products.find({"category_id": cat_id_str}))
                
                matched_products = []
                for p in prods:
                    matched_products.append({
                        "id": str(p["_id"]),
                        "name": p.get("name"),
                        "sku": p.get("sku", ""),
                        "type": "standard",
                        "link": f"/products/{str(p['_id'])}",
                        "image": p.get("image") or ""
                    })
                    
                cat_name_lower = exact_category.get("name", "").lower()
                if "ev" in cat_name_lower:
                    for p in db.ev_products.find():
                        matched_products.append({
                            "id": str(p["_id"]),
                            "name": p.get("title"),
                            "sku": "",
                            "type": "ev",
                            "link": "/ev-products",
                            "image": p.get("image") or ""
                        })
                if "harness" in cat_name_lower:
                    for p in db.harness_products.find():
                        matched_products.append({
                            "id": str(p["_id"]),
                            "name": p.get("title"),
                            "sku": "",
                            "type": "harness",
                            "link": "/wire-harness-products",
                            "image": p.get("image") or ""
                        })
                        
                suggestions = ["Request a Quote", "Show Categories", "Chat on WhatsApp"]
                if matched_products:
                    print("[Chatbot Routing Log]")
                    print(f"  User Query: \"{query}\"")
                    print(f"  Detected Intent: CATEGORY_CLICK")
                    print(f"  Product Results Count: {len(matched_products)}")
                    print(f"  FAQ Results Count: 0")
                    print(f"  Final Route Chosen: CATEGORY_CLICK")
                    
                    return {
                        "reply": f"Here are the products under the **{exact_category['name']}** category:",
                        "suggestions": suggestions,
                        "products": matched_products,
                        "categories": []
                    }
                else:
                    categories_list = [{
                        "id": cat_id_str,
                        "name": exact_category.get("name"),
                        "description": exact_category.get("description") or "",
                        "image": exact_category.get("image") or "",
                        "link": f"/products?category={cat_id_str}"
                    }]
                    print("[Chatbot Routing Log]")
                    print(f"  User Query: \"{query}\"")
                    print(f"  Detected Intent: CATEGORY_CLICK")
                    print(f"  Product Results Count: 0")
                    print(f"  FAQ Results Count: 0")
                    print(f"  Final Route Chosen: CATEGORY_CLICK")
                    return {
                        "reply": f"Here is the details for the **{exact_category['name']}** category:",
                        "suggestions": suggestions,
                        "products": [],
                        "categories": categories_list
                    }
        except Exception as e:
            print(f"Error checking exact category click: {e}")

        # 1. Detect Intent
        intent = RagEngine.classify_intent(query)
        final_route = intent
        
        # Setup fallback settings
        settings = db.chatbot_settings.find_one({"_id": "global_settings"})
        fallback_msg = settings.get("fallbackMessage") if settings else "I'm sorry, I couldn't find an answer to your question. Would you like to submit an inquiry or contact us on WhatsApp?"
        
        def get_intent_response(intent_name: str) -> Optional[str]:
            try:
                intent_doc = db.chatbot_intents.find_one({"intent": {"$regex": f"^{intent_name}$", "$options": "i"}, "isActive": True})
                if intent_doc:
                    return intent_doc.get("response")
            except Exception as e:
                print(f"Error fetching intent response for {intent_name}: {e}")
            return None

        # FAQ Fallback Search Helper
        def search_faqs_fallback(query_str: str, query_clean_str: str) -> Optional[Dict[str, Any]]:
            nonlocal faq_count
            matched_faq = None
            faq_cnt = 0
            try:
                faqs = list(db.chatbot_faqs.find({}))
                for faq in faqs:
                    q_clean = re.sub(r'[^\w\s]', '', faq.get("question", "").strip().lower())
                    is_match = False
                    if q_clean and (q_clean in query_clean_str or query_clean_str in q_clean):
                        is_match = True
                    else:
                        for kw in faq.get("keywords", []):
                            kw_clean = re.sub(r'[^\w\s]', '', kw.strip().lower())
                            if kw_clean and (kw_clean == query_clean_str or f" {kw_clean} " in f" {query_clean_str} "):
                                is_match = True
                                break
                    if is_match:
                        faq_cnt += 1
                        if not matched_faq:
                            matched_faq = faq
            except Exception:
                pass
                
            if matched_faq:
                faq_count = faq_cnt
                return {
                    "reply": matched_faq.get("answer"),
                    "suggestions": ["Show Categories", "Submit Inquiry", "Chat on WhatsApp"],
                    "products": [],
                    "categories": []
                }
                
            embed_model = get_embedding_model()
            collection = get_collection()
            try:
                stored_count = collection.count()
            except Exception:
                stored_count = 0
            if stored_count > 0:
                query_vector = embed_model.encode(query_str).tolist()
                results = collection.query(query_embeddings=[query_vector], n_results=5)
                if results and results["documents"] and len(results["documents"][0]) > 0:
                    distances = results["distances"][0]
                    docs = results["documents"][0]
                    metas = results["metadatas"][0]
                    for idx, doc in enumerate(docs):
                        if distances[idx] > 1.35:
                            continue
                        source_type = metas[idx].get("source")
                        if source_type in ["pdf", "blog", "category"]:
                            faq_count = 1
                            categories_list = []
                            if source_type == "category":
                                reply = f"Here is some information about the **{metas[idx].get('name')}** category:"
                                suggestions = ["Show Categories", "Ask something else", "Chat on WhatsApp"]
                                try:
                                    from bson import ObjectId
                                    cat_doc = db.categories.find_one({"_id": ObjectId(metas[idx].get("id"))})
                                    if cat_doc:
                                        categories_list.append({
                                            "id": str(cat_doc["_id"]),
                                            "name": cat_doc.get("name"),
                                            "description": cat_doc.get("description") or "",
                                            "image": cat_doc.get("image") or "",
                                            "link": f"/products?category={str(cat_doc['_id'])}"
                                        })
                                except Exception:
                                    pass
                            elif source_type == "blog":
                                reply = f"Based on our blog post **\"{metas[idx].get('name')}\"**:\n\n{doc}"
                                suggestions = ["Ask something else", "Connect on WhatsApp"]
                            elif source_type == "pdf":
                                reply = doc
                                suggestions = ["Request a Quote", "Ask something else", "Chat on WhatsApp"]
                            else:
                                reply = doc
                                suggestions = ["Ask something else", "Connect on WhatsApp"]
                                
                            return {
                                "reply": reply,
                                "suggestions": suggestions,
                                "products": [],
                                "categories": categories_list
                            }
            return None

        # Execute Route based on Intent
        if intent == "QUOTE_REQUEST":
            resp = get_intent_response("QUOTE_REQUEST") or "Please fill out the form below to submit your inquiry directly to our sales team:"
            result = {
                "reply": resp,
                "suggestions": ["Show Categories", "Chat on WhatsApp"],
                "products": [],
                "categories": [],
                "isLeadForm": True
            }
            
        elif intent == "CONTACT":
            resp = get_intent_response("CONTACT") or "You can reach us at sales@aajtechtrading.com or call our team."
            result = {
                "reply": resp,
                "suggestions": ["Submit Inquiry", "Show Categories", "Chat on WhatsApp"],
                "products": [],
                "categories": []
            }
            
        elif intent == "SHIPPING":
            resp = get_intent_response("SHIPPING") or "We offer prompt shipping and dispatch. Please contact sales for specific delivery schedules."
            result = {
                "reply": resp,
                "suggestions": ["Submit Inquiry", "Show Categories", "Chat on WhatsApp"],
                "products": [],
                "categories": []
            }
            
        elif intent == "PRODUCT_SEARCH":
            # Search products only. Skip FAQ retrieval completely.
            matched_products = []
            seen_names = set()
            
            # Direct matches standard products
            for p in db.products.find({"$or": [{"name": {"$regex": query_clean, "$options": "i"}}, {"sku": {"$regex": query_clean, "$options": "i"}}]}):
                if p["name"] not in seen_names:
                    seen_names.add(p["name"])
                    matched_products.append({
                        "id": str(p["_id"]),
                        "name": p.get("name"),
                        "sku": p.get("sku", ""),
                        "type": "standard",
                        "link": f"/products/{str(p['_id'])}",
                        "image": p.get("image") or ""
                    })
                    
            # Direct matches EV products
            for p in db.ev_products.find({"title": {"$regex": query_clean, "$options": "i"}}):
                if p["title"] not in seen_names:
                    seen_names.add(p["title"])
                    matched_products.append({
                        "id": str(p["_id"]),
                        "name": p.get("title"),
                        "sku": "",
                        "type": "ev",
                        "link": "/ev-products",
                        "image": p.get("image") or ""
                    })
                    
            # Direct matches Harness products
            for p in db.harness_products.find({"title": {"$regex": query_clean, "$options": "i"}}):
                if p["title"] not in seen_names:
                    seen_names.add(p["title"])
                    matched_products.append({
                        "id": str(p["_id"]),
                        "name": p.get("title"),
                        "sku": "",
                        "type": "harness",
                        "link": "/wire-harness-products",
                        "image": p.get("image") or ""
                    })
                    
            # ChromaDB product search fallback
            if len(matched_products) < 3:
                embed_model = get_embedding_model()
                collection = get_collection()
                try:
                    stored_count = collection.count()
                except Exception:
                    stored_count = 0
                if stored_count > 0:
                    query_vector = embed_model.encode(query).tolist()
                    results = collection.query(query_embeddings=[query_vector], n_results=5)
                    if results and results["documents"] and len(results["documents"][0]) > 0:
                        distances = results["distances"][0]
                        metas = results["metadatas"][0]
                        for idx, meta in enumerate(metas):
                            if distances[idx] > 1.35:
                                continue
                            entity_id = meta.get("id")
                            entity_name = meta.get("name")
                            source_type = meta.get("source")
                            if entity_id and entity_name not in seen_names and source_type in ["product", "ev_product", "harness_product"]:
                                # Fetch image URL from MongoDB
                                from bson import ObjectId
                                img_url = ""
                                try:
                                    if source_type == "product":
                                        p = db.products.find_one({"_id": ObjectId(entity_id)})
                                        if p: img_url = p.get("image") or ""
                                    elif source_type == "ev_product":
                                        p = db.ev_products.find_one({"_id": ObjectId(entity_id)})
                                        if p: img_url = p.get("image") or ""
                                    elif source_type == "harness_product":
                                        p = db.harness_products.find_one({"_id": ObjectId(entity_id)})
                                        if p: img_url = p.get("image") or ""
                                except Exception:
                                    pass
                                
                                seen_names.add(entity_name)
                                matched_products.append({
                                    "id": entity_id,
                                    "name": entity_name,
                                    "sku": meta.get("sku", ""),
                                    "type": meta.get("type", "standard"),
                                    "link": meta.get("link", ""),
                                    "image": img_url
                                })
                                if len(matched_products) >= 3:
                                    break
                                    
            if matched_products:
                product_count = len(matched_products)
                result = {
                    "reply": "I found these matching products from our database. Select a product to view details:",
                    "suggestions": ["Request a Quote", "Show Categories", "Chat on WhatsApp"],
                    "products": matched_products[:3],
                    "categories": []
                }
            else:
                # Fallback to FAQ if no product found
                faq_res = search_faqs_fallback(query, query_clean)
                if faq_res:
                    final_route = "PRODUCT_SEARCH_TO_FAQ"
                    result = faq_res
                else:
                    result = {
                        "reply": fallback_msg,
                        "suggestions": ["Submit Inquiry", "Chat on WhatsApp", "Show Categories"],
                        "products": [],
                        "categories": []
                    }
                
        elif intent == "PRODUCT_INFO":
            # Search product details/descriptions only. Skip FAQ retrieval completely.
            embed_model = get_embedding_model()
            collection = get_collection()
            try:
                stored_count = collection.count()
            except Exception:
                stored_count = 0
            if stored_count == 0:
                RagEngine.index_data(db)
                
            query_vector = embed_model.encode(query).tolist()
            results = collection.query(query_embeddings=[query_vector], n_results=5)
            
            valid_matches = []
            seen_ids = set()
            matched_products = []
            
            if results and results["documents"] and len(results["documents"][0]) > 0:
                distances = results["distances"][0]
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                
                for idx, doc in enumerate(docs):
                    if distances[idx] > 1.35:
                        continue
                    source_type = metas[idx].get("source")
                    if source_type in ["product", "ev_product", "harness_product"]:
                        valid_matches.append((doc, metas[idx]))
                        entity_id = metas[idx].get("id")
                        if entity_id and entity_id not in seen_ids:
                            seen_ids.add(entity_id)
                            # Fetch image URL from MongoDB
                            from bson import ObjectId
                            img_url = ""
                            try:
                                if source_type == "product":
                                    p = db.products.find_one({"_id": ObjectId(entity_id)})
                                    if p: img_url = p.get("image") or ""
                                elif source_type == "ev_product":
                                    p = db.ev_products.find_one({"_id": ObjectId(entity_id)})
                                    if p: img_url = p.get("image") or ""
                                elif source_type == "harness_product":
                                    p = db.harness_products.find_one({"_id": ObjectId(entity_id)})
                                    if p: img_url = p.get("image") or ""
                            except Exception:
                                pass
                                
                            matched_products.append({
                                "id": entity_id,
                                "name": metas[idx].get("name"),
                                "sku": metas[idx].get("sku", ""),
                                "type": metas[idx].get("type", "standard"),
                                "link": metas[idx].get("link", ""),
                                "image": img_url
                            })
                            
            if valid_matches:
                best_doc, best_meta = valid_matches[0]
                entity_name = best_meta.get("name")
                product_count = len(matched_products)
                result = {
                    "reply": f"Here is the product details for **{entity_name}**:\n\n{best_doc}",
                    "suggestions": ["Request a Quote", "Ask something else", "Connect on WhatsApp"],
                    "products": matched_products[:3],
                    "categories": []
                }
            else:
                # Fallback to FAQ if no product found
                faq_res = search_faqs_fallback(query, query_clean)
                if faq_res:
                    final_route = "PRODUCT_INFO_TO_FAQ"
                    result = faq_res
                else:
                    result = {
                        "reply": fallback_msg,
                        "suggestions": ["Submit Inquiry", "Chat on WhatsApp", "Show Categories"],
                        "products": [],
                        "categories": []
                    }
                
        elif intent == "FAQ":
            # Search FAQ knowledge base only
            matched_faq = None
            faq_count = 0
            try:
                faqs = list(db.chatbot_faqs.find({}))
                for faq in faqs:
                    q_clean = re.sub(r'[^\w\s]', '', faq.get("question", "").strip().lower())
                    is_match = False
                    if q_clean and (q_clean in query_clean or query_clean in q_clean):
                        is_match = True
                    else:
                        for kw in faq.get("keywords", []):
                            kw_clean = re.sub(r'[^\w\s]', '', kw.strip().lower())
                            if kw_clean and (kw_clean == query_clean or f" {kw_clean} " in f" {query_clean} "):
                                is_match = True
                                break
                    if is_match:
                        faq_count += 1
                        if not matched_faq:
                            matched_faq = faq
            except Exception as e:
                print(f"Error matching chatbot_faqs: {e}")
                
            if matched_faq:
                result = {
                    "reply": matched_faq.get("answer"),
                    "suggestions": ["Show Categories", "Submit Inquiry", "Chat on WhatsApp"],
                    "products": [],
                    "categories": []
                }
            else:
                # Fallback: run ChromaDB similarity search restricted to non-product sources (pdf, blog, category)
                embed_model = get_embedding_model()
                collection = get_collection()
                try:
                    stored_count = collection.count()
                except Exception:
                    stored_count = 0
                if stored_count == 0:
                    RagEngine.index_data(db)
                    
                query_vector = embed_model.encode(query).tolist()
                results = collection.query(query_embeddings=[query_vector], n_results=5)
                
                best_doc = None
                best_meta = None
                if results and results["documents"] and len(results["documents"][0]) > 0:
                    distances = results["distances"][0]
                    docs = results["documents"][0]
                    metas = results["metadatas"][0]
                    
                    for idx, doc in enumerate(docs):
                        if distances[idx] > 1.35:
                            continue
                        source_type = metas[idx].get("source")
                        if source_type in ["pdf", "blog", "category"]:
                            best_doc = doc
                            best_meta = metas[idx]
                            faq_count = 1
                            break
                            
                if best_doc and best_meta:
                    source_type = best_meta.get("source")
                    entity_name = best_meta.get("name")
                    categories_list = []
                    
                    if source_type == "category":
                        reply = f"Here is some information about the **{entity_name}** category:"
                        suggestions = ["Show Categories", "Ask something else", "Chat on WhatsApp"]
                        try:
                            from bson import ObjectId
                            cat_doc = db.categories.find_one({"_id": ObjectId(best_meta.get("id"))})
                            if cat_doc:
                                categories_list.append({
                                    "id": str(cat_doc["_id"]),
                                    "name": cat_doc.get("name"),
                                    "description": cat_doc.get("description") or "",
                                    "image": cat_doc.get("image") or "",
                                    "link": f"/products?category={str(cat_doc['_id'])}"
                                })
                        except Exception:
                            pass
                    elif source_type == "blog":
                        reply = f"Based on our blog post **\"{entity_name}\"**:\n\n{best_doc}"
                        suggestions = ["Ask something else", "Connect on WhatsApp"]
                    elif source_type == "pdf":
                        reply = best_doc
                        suggestions = ["Request a Quote", "Ask something else", "Chat on WhatsApp"]
                    else:
                        reply = best_doc
                        suggestions = ["Ask something else", "Connect on WhatsApp"]
                        
                    result = {
                        "reply": reply,
                        "suggestions": suggestions,
                        "products": [],
                        "categories": categories_list
                    }
                else:
                    result = {
                        "reply": fallback_msg,
                        "suggestions": ["Submit Inquiry", "Chat on WhatsApp", "Products Offered"],
                        "products": [],
                        "categories": []
                    }
                    
        else: # GENERAL
            # Check Greetings first
            matched_greeting = None
            for group in GREETINGS_MAP:
                for kw in group["keywords"]:
                    kw_clean = kw.strip().lower()
                    if query_clean == kw_clean or query_clean.startswith(kw_clean):
                        matched_greeting = group
                        break
                if matched_greeting:
                    break

            if matched_greeting:
                reply = matched_greeting["default_reply"]
                if matched_greeting["name"] == "standard":
                    try:
                        settings = db.chatbot_settings.find_one({"_id": "global_settings"})
                        if settings and settings.get("greetingMessage"):
                            reply = settings["greetingMessage"]
                    except Exception:
                        pass
                
                result = {
                    "reply": reply,
                    "suggestions": ["Products Offered", "Submit Inquiry", "Chat on WhatsApp"],
                    "products": [],
                    "categories": []
                }
            else:
                # Check Category list intent
                category_intents = [
                    "show product categories", "show categories", "list categories", "view categories", 
                    "what categories", "product categories", "categories", 
                    "type of product", "types of product", "type of products", "types of products", 
                    "kind of product", "kinds of product", "kind of products", "kinds of products",
                    "what kind of product", "what kinds of products", "what kind of products",
                    "how many type", "how many types", "how many product", "how many products",
                    "range of product", "range of products", "product range", "product ranges",
                    "what products", "products offered", "show products", "list products", 
                    "view products", "what products", "products", "show me the product",
                    "show me the products", "show me product", "show me products", "show product",
                    "list product", "view product", "product", "all products", "all product",
                    "show all products", "show all product", "all categories", "show all categories",
                    "show items", "show item", "list items", "list item", "view items", "view item",
                    "all items", "all item", "show all items", "show all item",
                    "show me the item", "show me the items", "show me item", "show me items", "show me your items", "show me your item",
                    "what items", "what item", "items offered", "item offered",
                    "types of items", "types of item", "kinds of items", "kinds of item",
                    "item range", "item ranges", "range of items", "range of item",
                    "items", "item"
                ]
                if any(intent_kw in query_clean for intent_kw in category_intents) or query_clean in ["categories", "products", "product", "items", "item"]:
                    try:
                        cats = list(db.categories.find().sort("sequence", 1))
                        if cats:
                            reply = "Here are the product categories we offer. Select any category to view more details:"
                            suggestions = [cat.get("name") for cat in cats[:3]]
                            suggestions.extend(["Submit Inquiry", "Chat on WhatsApp"])
                            
                            categories_list = []
                            for cat in cats:
                                categories_list.append({
                                    "id": str(cat["_id"]),
                                    "name": cat.get("name"),
                                    "description": cat.get("description") or "",
                                    "image": cat.get("image") or "",
                                    "link": f"/products?category={str(cat['_id'])}"
                                })
                            
                            result = {
                                "reply": reply,
                                "suggestions": suggestions,
                                "products": [],
                                "categories": categories_list
                            }
                        else:
                            result = None
                    except Exception:
                        result = None
                else:
                    result = None
                    
                # Check Product list intent
                if not result:
                    product_intents = [
                        "products offered", "show products", "list products", "view products", 
                        "what products", "products", "types of products", "kinds of products",
                        "product range", "product ranges", "range of products", "show me the product",
                        "show me the products", "show me product", "show me products", "show product",
                        "list product", "view product", "product", "all products", "all product",
                        "show all products", "show all product", "all categories", "show all categories",
                        "show items", "show item", "list items", "list item", "view items", "view item",
                        "all items", "all item", "show all items", "show all item",
                        "show me the item", "show me the items", "show me item", "show me items", "show me your items", "show me your item",
                        "what items", "what item", "items offered", "item offered",
                        "types of items", "types of item", "kinds of items", "kinds of item",
                        "item range", "item ranges", "range of items", "range of item",
                        "items", "item"
                    ]
                    if any(intent_kw in query_clean for intent_kw in product_intents) or query_clean in ["products", "product", "items", "item"]:
                        try:
                            cats = list(db.categories.find().sort("sequence", 1))
                            if cats:
                                reply = "We offer a wide range of industrial components. Select a category below to browse the products:"
                                suggestions = [cat.get("name") for cat in cats[:3]]
                                suggestions.extend(["Submit Inquiry", "Chat on WhatsApp"])
                                
                                categories_list = []
                                for cat in cats:
                                    categories_list.append({
                                        "id": str(cat["_id"]),
                                        "name": cat.get("name"),
                                        "description": cat.get("description") or "",
                                        "image": cat.get("image") or "",
                                        "link": f"/products?category={str(cat['_id'])}"
                                    })
                                
                                result = {
                                    "reply": reply,
                                    "suggestions": suggestions,
                                    "products": [],
                                    "categories": categories_list
                                }
                        except Exception:
                            pass
                            
                # Exact category name match
                if not result:
                    try:
                        exact_category = db.categories.find_one({"name": {"$regex": f"^{re.escape(query.strip())}$", "$options": "i"}})
                        if exact_category:
                            cat_id_str = str(exact_category["_id"])
                            prods = list(db.products.find({"category_id": cat_id_str}))
                            suggestions = ["Request a Quote", "Show Categories", "Chat on WhatsApp"]
                            
                            if prods:
                                matched_products = []
                                for p in prods:
                                    matched_products.append({
                                        "id": str(p["_id"]),
                                        "name": p.get("name"),
                                        "sku": p.get("sku", ""),
                                        "type": "standard",
                                        "link": f"/products/{str(p['_id'])}",
                                        "image": p.get("image") or ""
                                    })
                                result = {
                                    "reply": f"Here are the products under the **{exact_category['name']}** category:",
                                    "suggestions": suggestions,
                                    "products": matched_products,
                                    "categories": []
                                }
                            else:
                                categories_list = [{
                                    "id": cat_id_str,
                                    "name": exact_category.get("name"),
                                    "description": exact_category.get("description") or "",
                                    "image": exact_category.get("image") or "",
                                    "link": f"/products?category={cat_id_str}"
                                }]
                                result = {
                                    "reply": f"Here is the details for the **{exact_category['name']}** category:",
                                    "suggestions": suggestions,
                                    "products": [],
                                    "categories": categories_list
                                }
                    except Exception:
                        pass
                        
                # Default general RAG Search over all sources
                if not result:
                    embed_model = get_embedding_model()
                    collection = get_collection()
                    try:
                        stored_count = collection.count()
                    except Exception:
                        stored_count = 0
                    if stored_count == 0:
                        RagEngine.index_data(db)
                        
                    query_vector = embed_model.encode(query).tolist()
                    results = collection.query(query_embeddings=[query_vector], n_results=3)
                    
                    if not results or not results["documents"] or len(results["documents"][0]) == 0:
                        faq_res = search_faqs_fallback(query, query_clean)
                        if faq_res:
                            final_route = "GENERAL_TO_FAQ"
                            result = faq_res
                        else:
                            result = {
                                "reply": fallback_msg,
                                "suggestions": ["Submit Inquiry", "Chat on WhatsApp", "Products Offered"],
                                "products": [],
                                "categories": []
                            }
                    else:
                        distances = results["distances"][0]
                        docs = results["documents"][0]
                        metas = results["metadatas"][0]
                        
                        valid_matches = []
                        seen_ids = set()
                        matched_products = []
                        
                        for idx, doc in enumerate(docs):
                            if distances[idx] > 1.35:
                                continue
                            valid_matches.append((doc, metas[idx]))
                            
                            entity_id = metas[idx].get("id")
                            if entity_id and entity_id not in seen_ids:
                                seen_ids.add(entity_id)
                                if metas[idx].get("source") in ["product", "ev_product", "harness_product"]:
                                    # Fetch image URL from MongoDB
                                    from bson import ObjectId
                                    img_url = ""
                                    try:
                                        if metas[idx].get("source") == "product":
                                            p = db.products.find_one({"_id": ObjectId(entity_id)})
                                            if p: img_url = p.get("image") or ""
                                        elif metas[idx].get("source") == "ev_product":
                                            p = db.ev_products.find_one({"_id": ObjectId(entity_id)})
                                            if p: img_url = p.get("image") or ""
                                        elif metas[idx].get("source") == "harness_product":
                                            p = db.harness_products.find_one({"_id": ObjectId(entity_id)})
                                            if p: img_url = p.get("image") or ""
                                    except Exception:
                                        pass
                                        
                                    matched_products.append({
                                        "id": entity_id,
                                        "name": metas[idx].get("name"),
                                        "sku": metas[idx].get("sku", ""),
                                        "type": metas[idx].get("type", "standard"),
                                        "link": metas[idx].get("link", ""),
                                        "image": img_url
                                    })
                                    
                        if not valid_matches:
                            faq_res = search_faqs_fallback(query, query_clean)
                            if faq_res:
                                final_route = "GENERAL_TO_FAQ"
                                result = faq_res
                            else:
                                result = {
                                    "reply": fallback_msg,
                                    "suggestions": ["Submit Inquiry", "Chat on WhatsApp", "Show Categories"],
                                    "products": [],
                                    "categories": []
                                }
                        else:
                            best_doc, best_meta = valid_matches[0]
                            source_type = best_meta.get("source")
                            entity_name = best_meta.get("name")
                            categories_list = []
                            
                            if source_type in ["product", "ev_product", "harness_product"]:
                                reply = "I found these matching products from our database. Select a product to view details:"
                                suggestions = ["Request a Quote", "Ask something else", "Connect on WhatsApp"]
                                product_count = len(matched_products)
                            elif source_type == "category":
                                reply = f"Here is some information about the **{entity_name}** category:"
                                suggestions = ["Show Categories", "Ask something else", "Chat on WhatsApp"]
                                try:
                                    from bson import ObjectId
                                    cat_doc = db.categories.find_one({"_id": ObjectId(best_meta.get("id"))})
                                    if cat_doc:
                                        categories_list.append({
                                            "id": str(cat_doc["_id"]),
                                            "name": cat_doc.get("name"),
                                            "description": cat_doc.get("description") or "",
                                            "image": cat_doc.get("image") or "",
                                            "link": f"/products?category={str(cat_doc['_id'])}"
                                        })
                                except Exception:
                                    pass
                            elif source_type == "blog":
                                reply = f"Based on our blog post **\"{entity_name}\"**:\n\n{best_doc}"
                                suggestions = ["Ask something else", "Connect on WhatsApp"]
                            elif source_type == "pdf":
                                reply = best_doc
                                suggestions = ["Request a Quote", "Ask something else", "Chat on WhatsApp"]
                                faq_count = 1
                            else:
                                reply = best_doc
                                suggestions = ["Ask something else", "Connect on WhatsApp"]
                                
                            result = {
                                "reply": reply,
                                "suggestions": suggestions,
                                "products": matched_products,
                                "categories": categories_list
                            }
                            
        # Print routing logs to console
        print("[Chatbot Routing Log]")
        print(f"  User Query: \"{query}\"")
        print(f"  Detected Intent: {intent}")
        print(f"  Product Results Count: {product_count}")
        print(f"  FAQ Results Count: {faq_count}")
        print(f"  Final Route Chosen: {final_route}")
        
        return result


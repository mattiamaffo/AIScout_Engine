"""
AIScout Brain - Modulo Cloud
Fornisce funzioni per ricerca similarità, generazione report e Routing intelligente.
Configurato per Groq (LLM), FastEmbed (Embeddings), Qdrant Cloud.
"""

import os
import sys
import uuid
import time
import joblib # type: ignore
import pandas as pd # type: ignore
import dspy # type: ignore
from dotenv import load_dotenv # type: ignore
from tavily import TavilyClient # type: ignore
from qdrant_client import QdrantClient, models # type: ignore
from fastembed import TextEmbedding # type: ignore

# Carica variabili d'ambiente
load_dotenv()

# --- CONFIGURAZIONE CLOUD ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

COLLECTION_NAME = "scouting_reports"
GROQ_MODEL = "llama-3.3-70b-versatile" 
VECTOR_SIZE = 384 

# --- SINGLETON PATTERN PER INIZIALIZZAZIONE ---
_INITIALIZED = False
_sim_engine = None
_df_main = None
_tavily = None
_qdrant = None
_embedding_model = None
_scout_bot = None
_router_bot = None  # <--- NUOVO

def _initialize():
    """Inizializza tutti i componenti (lazy loading)."""
    global _INITIALIZED, _sim_engine, _df_main, _tavily, _qdrant, _embedding_model, _scout_bot, _router_bot
    
    if _INITIALIZED:
        return
    
    print("[INIT] Caricamento AIScout Brain...", file=sys.stderr)
    
    # 1. Carica dati e motore similarità
    try:
        import data
        from SimEngine import SimilarityEngine
        
        if data.DATABASE_DF.empty:
            data.load_data()
            
        _df_main = data.DATABASE_DF
        artifacts_path = data.ARTIFACTS_DIR
        
        _sim_engine = SimilarityEngine(artifacts_dir=artifacts_path)
        _sim_engine._ensure_artifacts_loaded()
        print("[INIT] ✓ SimEngine caricato", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] SimEngine: {e}", file=sys.stderr)
        raise
    
    # 2. Configura DSPy con Groq
    try:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY non trovata nel .env")
        
        lm = dspy.LM(model=f'groq/{GROQ_MODEL}', api_key=GROQ_API_KEY, temperature=0.0) # Temp 0 per il router è meglio
        dspy.configure(lm=lm)
        
        # --- CLASSI DSPy ---
        class ScoutingSignature(dspy.Signature):
            """Senior Football Scout analysis. RESPOND STRICTLY IN ITALIAN."""
            player_name = dspy.InputField()
            raw_notes = dspy.InputField()
            player_profile = dspy.OutputField(desc="In Italian")
            tactical_analysis = dspy.OutputField(desc="In Italian")
            key_strengths = dspy.OutputField(desc="In Italian")
            weaknesses = dspy.OutputField(desc="In Italian")
            final_verdict = dspy.OutputField(desc="In Italian")
        
        class ScoutBot(dspy.Module):
            def __init__(self):
                super().__init__()
                self.prog = dspy.ChainOfThought(ScoutingSignature)
            def forward(self, name, notes):
                return self.prog(player_name=name, raw_notes=notes)
        
        # --- NUOVO: ROUTER INTELLIGENTE ---
        class RouterSignature(dspy.Signature):
            """
            You are an AI Orchestrator for a Football Scouting App.
            Classify the user query into a specific TOOL and extract the PLAYER NAME.
            
            TOOLS AVAILABLE:
            - 'SEARCH_SIMILAR': User wants to find similar players based on stats (e.g. "Who is similar to...", "Find replacement for...", "Statistical twins of...").
            - 'GET_REPORT': User wants a detailed tactical analysis or report (e.g. "Analyze...", "Scouting report of...", "How does X play?", "Strengths of...").
            - 'CHAT': General conversation, greetings, or questions unrelated to a specific player lookup.
            """
            user_query = dspy.InputField()
            tool_selected = dspy.OutputField(desc="Must be exactly one of: 'SEARCH_SIMILAR', 'GET_REPORT', 'CHAT'")
            player_name = dspy.OutputField(desc="The name of the target player extracted from query. If CHAT, leave empty.")
            chat_reply = dspy.OutputField(desc="If tool is CHAT, write a friendly reply here IN ITALIAN. Otherwise leave empty.")

        class RouterBot(dspy.Module):
            def __init__(self):
                super().__init__()
                self.prog = dspy.ChainOfThought(RouterSignature)
            def forward(self, query):
                return self.prog(user_query=query)

        _scout_bot = ScoutBot()
        _router_bot = RouterBot() # Inizializziamo il router
        print("[INIT] ✓ DSPy & Router configurati (Groq)", file=sys.stderr)

    except Exception as e:
        print(f"[ERROR] DSPy/Groq: {e}", file=sys.stderr)
        raise
    
    # 3. Client Esterni
    try:
        _tavily = TavilyClient(api_key=TAVILY_API_KEY)
        _qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        if not _qdrant.collection_exists(COLLECTION_NAME):
            _qdrant.create_collection(collection_name=COLLECTION_NAME, vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE))
        
        _qdrant.create_payload_index(collection_name=COLLECTION_NAME, field_name="player_name", field_schema=models.PayloadSchemaType.KEYWORD)
        print("[INIT] ✓ Tavily & Qdrant configurati", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] External Clients: {e}", file=sys.stderr)
        raise
    
    # 4. FastEmbed
    try:
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        print("[INIT] ✓ FastEmbed caricato", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] FastEmbed: {e}", file=sys.stderr)
        raise
    
    _INITIALIZED = True
    print("[INIT] ✓ AIScout Brain pronto\n", file=sys.stderr)


def initialize():
    """Wrapper pubblico per l'inizializzazione."""
    _initialize()

# --- FUNZIONI CORE ---

def cerca_simili_statistici(nome_giocatore: str) -> str:
    _initialize()
    try:
        print(f"[DEBUG] Cerco simili a: {nome_giocatore}...") # DEBUG
        
        df_res, player_style = _sim_engine.find_similar_players(nome_giocatore, k=5)
        
        # DEBUG: Stampiamo cosa ha restituito il motore
        print(f"[DEBUG] Righe trovate: {len(df_res)}")
        if not df_res.empty:
            print(f"[DEBUG] Colonne disponibili: {df_res.columns.tolist()}")
            print(f"[DEBUG] Primo risultato:\n{df_res.iloc[0]}")

        if df_res.empty:
            return f"Nessun giocatore simile trovato per '{nome_giocatore}'."
        
        cols_to_show = ['Player', 'Team', 'Comp', 'Age', 'Similarita (Distanza)']
        # Aggiungiamo 'Valore_Mercato' se c'è, che è utile
        if 'Valore_Mercato' in df_res.columns:
            cols_to_show.append('Valore_Mercato')

        cols_existing = [c for c in cols_to_show if c in df_res.columns]
        
        result = f"**Stile di Gioco:** {player_style}\n\n" if player_style else ""
        result += df_res[cols_existing].to_markdown(index=False)
        
        return result
        
    except Exception as e:
        print(f"[ERROR] cerca_simili_statistici: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc() # Stampa l'errore completo
        return f"Errore nella ricerca: {str(e)}"

def ottieni_report_tattico(nome_giocatore: str) -> str:
    _initialize()
    print(f"[LOG] Report richiesto per: {nome_giocatore}", file=sys.stderr)
    
    # 1. Cache
    try:
        hits = _qdrant.scroll(collection_name=COLLECTION_NAME, scroll_filter=models.Filter(must=[models.FieldCondition(key="player_name", match=models.MatchValue(value=nome_giocatore))]), limit=1)[0]
        if hits:
            return f"FONTE: MEMORIA INTERNA\n\n{hits[0].payload['full_text']}"
    except Exception:
        pass
    
    # 2. Disambiguazione
    search_context = ""
    try:
        player_row = _df_main[_df_main['Player'].str.lower() == nome_giocatore.lower()].head(1)
        if not player_row.empty:
            search_context = f"{player_row.iloc[0]['Team']} {player_row.iloc[0]['Pos']}"
    except Exception:
        pass
    
    # 3. Web
    try:
        response = _tavily.search(query=f"{nome_giocatore} {search_context} tactical analysis scouting report style of play", max_results=5, include_raw_content=True)
        raw_notes = "\n".join([r['content'] for r in response['results']])
        sources = "\n".join([f"- {r['url']}" for r in response['results']])
    except Exception as e:
        return f"Errore ricerca web: {str(e)}"
    
    # 4. GenAI
    try:
        notes_with_context = f"CONTEXT: Player is {nome_giocatore}, plays for {search_context}.\nLANGUAGE: ITALIAN (Must write the report in Italian).\n\nRAW NOTES:\n{raw_notes}"
        pred = _scout_bot(name=nome_giocatore, notes=notes_with_context)
        final_report = f"# REPORT: {nome_giocatore} ({search_context})\n\n## PROFILO\n{pred.player_profile}\n\n## TATTICA\n{pred.tactical_analysis}\n\n## PRO\n{pred.key_strengths}\n\n## CONTRO\n{pred.weaknesses}\n\n## VERDETTO\n{pred.final_verdict}\n\n---\nFONTI:\n{sources}"
    except Exception as e:
        return f"Errore generazione report: {str(e)}"
    
    # 5. Save
    try:
        embedding_vector = list(_embedding_model.embed([final_report]))[0].tolist()
        _qdrant.upsert(collection_name=COLLECTION_NAME, points=[models.PointStruct(id=str(uuid.uuid4()), vector=embedding_vector, payload={"player_name": nome_giocatore, "full_text": final_report, "sources": sources})])
    except Exception:
        pass
    
    return f"FONTE: WEB + AI (Disambiguato)\n\n{final_report}"

# --- FUNZIONE MASTER PER LA WEB APP ---
def process_request(user_text: str) -> dict:
    """
    Punto di ingresso per la chat.
    Restituisce un dizionario: {'type': 'chat'|'table'|'report'|'error', 'content': str}
    """
    _initialize()
    
    print(f"[ROUTER] Input Utente: '{user_text}'", file=sys.stderr)
    
    try:
        # 1. Il Router decide cosa fare
        decision = _router_bot(query=user_text)
        tool = decision.tool_selected
        player = decision.player_name
        
        print(f"[ROUTER] Decisione: Tool={tool}, Player={player}", file=sys.stderr)
        
        if tool == 'SEARCH_SIMILAR':
            if not player or player.lower() == 'none':
                return {"type": "chat", "content": "Per cercare giocatori simili, devi dirmi il nome di un giocatore di riferimento."}
            content = cerca_simili_statistici(player)
            return {"type": "table", "content": content}
            
        elif tool == 'GET_REPORT':
            if not player or player.lower() == 'none':
                return {"type": "chat", "content": "Di quale giocatore vuoi il report? Specifica il nome."}
            content = ottieni_report_tattico(player)
            return {"type": "report", "content": content}
            
        else: # CHAT
            return {"type": "chat", "content": decision.chat_reply or "Sono un assistente tattico, chiedimi di analizzare un giocatore o trovarne di simili!"}
            
    except Exception as e:
        print(f"[ROUTER ERROR] {e}", file=sys.stderr)
        return {"type": "error", "content": f"Errore nel ragionamento: {e}"}

# --- TEST LOCALE ---
if __name__ == "__main__":
    print("\n=== TEST ROUTER ===")
    
    # Test 1: Domanda Statistica
    q1 = "Chi è simile a Calafiori?"
    print(f"\nQ: {q1}")
    res1 = process_request(q1)
    print(f"A ({res1['type']}): {str(res1['content'])[:100]}...") # Tronco per brevità
    
    # Test 2: Domanda Tattica
    q2 = "Analizza lo stile di gioco di Zirkzee"
    print(f"\nQ: {q2}")
    res2 = process_request(q2)
    print(f"A ({res2['type']}): {str(res2['content'])[:100]}...")
    
    # Test 3: Chat
    q3 = "Ciao, chi sei?"
    print(f"\nQ: {q3}")
    res3 = process_request(q3)
    print(f"A ({res3['type']}): {res3['content']}")
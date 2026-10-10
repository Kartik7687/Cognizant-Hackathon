

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from drugrag.eval.metrics import answer_text, cited_indices, is_refusal  # noqa: E402

st.set_page_config(page_title="Drug Label Q&A", page_icon="💊", layout="wide")

EXAMPLES = [
    "What are the contraindications of metformin?",
    "Can I take ibuprofen with warfarin?",
    "What are the common side effects of amlodipine?",
    "Should I double my warfarin dose?",
    "Does metformin cause hair to grow back?",
]

# --------------------------------------------------------------------------
# Loading (cache)
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading index and models...")
def load_retriever(index_dir: str, reranker: str):
    from drugrag.retrieval import Retriever
    return Retriever.from_dir(index_dir, reranker=reranker or None)


def get_answer_fn():
    try:
        from drugrag.generation.answer import answer  
        return answer, True
    except Exception:
        return None, False


def stub_answer(query: str, hits, mode: str) -> str:
    
    if not hits:
        return "Direct answer: Not found in the label.\n\n**Sources:** none"
    h = hits[0].chunk
    excerpt = h.text[:400].strip()
    return (f"**Direct answer:** (STUB, generation module not connected) See the {h.section} "
            f"section of the {h.drug_name} label [1].\n\n"
            f"**What the prescribing information says:** {excerpt}... [1]\n\n"
            f"**Important safety information:** This is not medical advice.\n\n"
            f"**What to do next:** Consult your doctor or pharmacist.\n\n"
            f"**Sources:** [1] {h.drug_name}, {h.section}")


def stream_text(text: str, delay: float = 0.012):
    """Typing effect for text that is already complete."""
    for tok in re.split(r"(\s+)", text):
        yield tok
        time.sleep(delay)


# --------------------------------------------------------------------------
# Highlighting: mark the sentences in a chunk that support the cited claim
# --------------------------------------------------------------------------
_STOP = set("the a an of and or to in for with on is are be may can that this it as by at from not no".split())


def _tokens(s: str):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in _STOP and len(w) > 2}


def _sentences(text: str):
    return [s for s in re.split(r"(?<=[.!?;:])\s+|\n+", text) if s.strip()]


def claims_for_citation(answer: str, n: int):
    """Sentences of the answer that cite [n]."""
    out = []
    for sent in _sentences(answer):
        if re.search(rf"\[[^\]]*\b{n}\b[^\]]*\]", sent):
            out.append(re.sub(r"\[[\d,\s]+\]", "", sent))
    return out


def highlight(chunk_text: str, claims, min_overlap: float = 0.34) -> str:
    claim_tokens = [_tokens(c) for c in claims if c.strip()]
    parts = []
    for sent in _sentences(chunk_text):
        st_tok = _tokens(sent)
        hit = False
        if st_tok:
            for ct in claim_tokens:
                if ct and len(st_tok & ct) / min(len(st_tok), len(ct)) >= min_overlap:
                    hit = True
                    break
        safe = sent.replace("<", "&lt;").replace(">", "&gt;")
        parts.append(f"<mark style='background:#fff3a3'>{safe}</mark>" if hit else safe)
    return "<div style='font-size:0.9rem;line-height:1.5'>" + " ".join(parts) + "</div>"


def source_header(c) -> str:
    return (f"{c.drug_name.title()} | {c.section} | v{getattr(c, 'version', '?')} | "
            f"{getattr(c, 'effective_date', 'n/a')} | page {getattr(c, 'page', 'N/A')}")




def render_sources(hits, answer: str):
    if not hits:
        return

    cited = set(cited_indices(answer))
    st.markdown("**Sources**")

    seen_sources = set()

    for i, h in enumerate(hits, start=1):
        c = h.chunk
        

        source_key = (
            getattr(c, "drug_name", ""),
            getattr(c, "section", ""),
            getattr(c, "text", "")
        )

        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)

        tag = "cited" if i in cited else "retrieved"

        with st.expander(
            f"[{i}] {source_header(c)} — {c.text[:70]}... ({tag}, score {h.score:.3f})",
            expanded=(i in cited and len(cited) <= 2)
        ):
            claims = claims_for_citation(answer, i) if i in cited else []
            st.markdown(
                highlight(c.text, claims),
                unsafe_allow_html=True
            )

            url = getattr(c, "source_url", "")
            if url:
                st.markdown(f"[Open on DailyMed]({url})")



# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.title("💊 Drug Label Q&A")
    mode = st.radio("Audience mode", ["clinician", "patient"],
                    format_func=lambda m: "🩺 Clinician" if m == "clinician" else "🙂 Patient / Caregiver")
    st.divider()
    st.subheader("Retrieval settings")
    index_dir = st.text_input("Index folder", "index/bge-small")
    reranker = st.text_input("Reranker (blank = none)", "bge-reranker-base")
    retr_mode = st.selectbox("Retrieval mode", ["hybrid_rerank", "hybrid", "dense", "bm25"])
    top_k = st.slider("Top-k passages", 2, 8, 5)
    st.divider()
    st.caption("Answers come only from official DailyMed drug labels. "
               "This tool does not give personal medical advice.")
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

try:
    retriever = load_retriever(index_dir, reranker)
    retriever_ok = True
except Exception as e:
    retriever, retriever_ok = None, False
    st.sidebar.error(f"Could not load retriever:\n{e}")

answer_fn, gen_ok = get_answer_fn()
if not gen_ok:
    st.sidebar.warning("Generation module not found, using STUB answers.")

# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------
st.title("Ask about a prescription drug")
st.caption("Clinician mode: technical and detailed. Patient mode: plain language with safety guidance.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# example buttons
cols = st.columns(len(EXAMPLES))
clicked = None
for col, ex in zip(cols, EXAMPLES):
    if col.button(ex, use_container_width=True):
        clicked = ex

# history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            if m.get("refused"):
                st.info("Safety response: personal medical decisions need a healthcare professional.")
            render_sources(m.get("hits", []), m["content"])

query = st.chat_input("Ask about indications, dosage, contraindications, side effects, interactions...") or clicked

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        if not retriever_ok:
            st.error("Retriever is not loaded. Check the index folder in the sidebar.")
        else:
            with st.spinner("Searching labels..."):
                res = retriever.retrieve(query, mode=retr_mode, top_k=top_k)
            hits = res.hits
            detected = getattr(res, "detected_drugs", [])
            if detected:
                st.caption(f"Detected drug(s): {', '.join(detected)}  |  retrieval: {retr_mode}")
            for note in getattr(res, "notes", []) or []:
                st.caption(f"Note: {note}")

           
            full = ""
            try:
                stream_fn = None
                try:
                    from drugrag.generation.answer import answer_stream  # optional
                    stream_fn = answer_stream
                except Exception:
                    pass
                if gen_ok and stream_fn:
                    full = st.write_stream(stream_fn(query, hits, mode))
                    result = full
                elif gen_ok:
                    with st.spinner("Generating answer..."):
                        result = answer_fn(query, hits, mode)
                    full = answer_text(result)
                    st.write_stream(stream_text(full))
                else:
                    full = stub_answer(query, hits, mode)
                    result = full
                    st.write_stream(stream_text(full))
            except Exception as e:
                full = f"Generation failed: {e}"
                result = full
                st.error(full)

            refused = is_refusal(result) if not isinstance(result, str) or gen_ok else False
            if refused:
                st.info("Safety response: personal medical decisions need a healthcare professional.")
            render_sources(hits, full)
            st.session_state.messages.append(
                {"role": "assistant", "content": full, "hits": hits, "refused": refused})
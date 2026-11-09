"""Minimal Streamlit chat UI wrapping the same RAG backend as src/main.py.

This is what the production container in the Dockerfile runs (Module 4).
You shouldn't need to change this file - it calls the same rag_answer()
you built, and traces every turn like the CLI does.

Run:
    streamlit run app.py
"""
import streamlit as st

from src.monitoring import log_turn
from src.rag import rag_answer

st.title("LumaBox Support Bot")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Ask about LumaBox policies...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    result = rag_answer(question)
    log_turn(result, channel="web")
    answer = result["answer"]
    sources = ", ".join(h["id"] for h in result["hits"])

    with st.chat_message("assistant"):
        st.write(answer)
        st.caption(f"Sources: {sources}")
    st.session_state.messages.append({"role": "assistant", "content": answer})

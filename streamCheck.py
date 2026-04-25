import streamlit as st
from dotenv import load_dotenv
import os
from rag import GraphRAGPipeline
import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)

load_dotenv()

st.set_page_config(page_title="SmartPlan", page_icon="🎓")
st.title("🎓 SmartPlan")
st.markdown("<p style='font-size:16px; color:gray;'>Conversational AI Academic Advising Agent for SJSU Students</p>", unsafe_allow_html=True)



if "pipeline" not in st.session_state:
    st.session_state.pipeline = GraphRAGPipeline(
        neo4j_uri         = os.getenv("NEO4J_URI",      "bolt://localhost:7687"),
        neo4j_user        = os.getenv("NEO4J_USER",     "neo4j"),
        neo4j_password    = os.getenv("NEO4J_PASSWORD", "password"),
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY"),
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle new input
if question := st.chat_input("Need an advisor? Ask me about your upcoming semester planning"):

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Querying advises..."):
            answer = st.session_state.pipeline.ask(question)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

with st.sidebar:
    st.header("Controls")
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.session_state.pipeline.reset_history()
        st.rerun()
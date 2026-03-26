# Disclaimer : This is not production ready code. Created only for Proof Of Concept
import os
from dotenv import load_dotenv
from pathlib import Path
from pprint import pprint

# LangChain + Neo4j + Ollama
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_ollama import ChatOllama
from langchain_community.graphs.graph_document import Node, Relationship, GraphDocument
from langchain_core.prompts import PromptTemplate

# pydexpi (deterministic parser + built-in graph exporter)
from pydexpi.loaders import ProteusSerializer
from pydexpi.loaders.ml_graph_loader import MLGraphLoader

from langchain_core.documents import Document

# ========================= CONFIG =========================
load_dotenv(dotenv_path='../.env')

NEO4J_URI      = "Your Neo4J URL"
NEO4J_USER     = "Neo4J UID"
NEO4J_PASSWORD = "Neo4J PWD"

# ========================= NEO4J AURA CONNECTION =========================
graph = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USER,
    password=NEO4J_PASSWORD,
    database="Your DataBase",          # change if your Aura DB name is different
    # refresh_schema=True
)

# ========================= LLM (local Ollama) =========================
llm = ChatOllama(
    model="llama3.1:8b",
    temperature=0,
    base_url="http://localhost:11434"
)

# Quick validation
result = graph.query("MATCH p=(:Student)-[:BELONGS_TO]->(:Department) RETURN p LIMIT 25")
pprint(result)

cypher_prompt = PromptTemplate.from_template("""
You are a Cypher expert. Only use types & properties that exist.
Instruction 1 : Get all nodes and relationships first in the graph first, print that information.
Instruction 2: And then use that information to answer the question. Do not make up any new data. 
Instruction 3: Only query the existing graph.
You are a Cypher expert. You **never** generate CREATE, MERGE, SET, DELETE, REMOVE unless the human explicitly says "create", "add", "insert", "update" or "delete".
For any analytical / reporting / counting / listing question → generate **only MATCH / OPTIONAL MATCH / RETURN** queries.
Do NOT generate example data. Do NOT insert anything. Cross check the answers by explicitly counting.
Question: {question}
""")

# ========================= 4. LLM QUERY CHAIN (Ollama local) =========================
qa_chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    verbose=True,                    # shows the Cypher it generates
    cypher_prompt=cypher_prompt,      # custom prompt to improve Cypher quality
    allow_dangerous_requests=True,    # required for Aura
    input_key="question"
)

# ========================= EXAMPLE QUERIES =========================
print("\n=== Try these queries ===")
queries = [
   # "List all nodes and relationships in the graph",
    "which department has the most students? and what is the name of department and list all the students name in that department",
]

for q in queries:
    print(f"\nQuestion: {q}")
    response = qa_chain.invoke({"question": q})
    print("Answer:", response["result"])

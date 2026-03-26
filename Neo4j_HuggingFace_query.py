# Disclaimer : This is not production ready code. Created only for Proof Of Concept
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
# pip install langchain langchain-community langchain-huggingface neo4j
# pip install transformers accelerate bitsandbytes
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    pipeline,
)
from langchain_huggingface import HuggingFacePipeline
from langchain_community.graphs import Neo4jGraph
from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_core.prompts import PromptTemplate

# ========================= CONFIG =========================
NEO4J_URL = "Your Neo4J URL"          # change if using Neo4j Aura / remote
NEO4J_USER = "Neo4J UID"
NEO4J_PASSWORD = "Neo4J PWD"        # ←←← CHANGE THIS

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct" # meta-llama/Llama-3.1-8B
# =========================================================

print("🔧 Loading Qwen2.5-1.5B-Instruct...")

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=quantization_config,
    device_map="auto",           # automatically puts layers on GPU
    #trust_remote_code=True,
    torch_dtype=torch.bfloat16,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=512,
    temperature=0.1,
    do_sample=False,
    top_p=0.95,
    repetition_penalty=1.15,
)

llm = HuggingFacePipeline(pipeline=pipe)

# ========================= Connect to Neo4j =========================
graph = Neo4jGraph(
    url=NEO4J_URL,
    username=NEO4J_USER,
    password=NEO4J_PASSWORD,
    database="YourDataBASE",          # change if using a different Neo4j database
    #refresh_schema=True,   # important so LLM knows your graph schema
)

# Better Cypher prompt (optional but helps)
CYPHER_GENERATION_TEMPLATE = """
Task: Generate a Cypher statement to query the graph database.
Use only the provided schema.
Do not include any explanation or extra text. Return ONLY the Cypher query.

Schema:
{schema}

Question: {question}

Cypher Query:
"""
cypher_prompt = PromptTemplate.from_template(CYPHER_GENERATION_TEMPLATE)

# Strict answer prompt
ANSWER_PROMPT_TEMPLATE = """
Answer the question using ONLY the information below.
Be extremely concise. Use bullet points or simple list if multiple items.
Do not add any introduction, conclusion, thanks, or extra help.

Question: {question}
Information: {context}

Answer:
"""

answer_prompt = PromptTemplate.from_template(ANSWER_PROMPT_TEMPLATE)

# ========================= Build the QA Chain =========================
chain = GraphCypherQAChain.from_llm(
    llm=llm, # The model that you have selected and loaded
    graph=graph, # the Neo4j graph connection
    cypher_prompt=cypher_prompt, # optional but helps the LLM generate better Cypher
    qa_prompt=answer_prompt, # optional but helps the LLM give better answers based on the query results
    verbose=False,           # shows the generated Cypher and query results in the console for debugging
    return_intermediate_steps=True, # important to return the generated Cypher so we can see it in the console (optional but helpful for debugging)
    allow_dangerous_requests=True,   # needed for local Neo4j
    input_key="question", # important since the default "query" key is being overridden
    
)

# ========================= Interactive Query Loop =========================
print("\n✅ Ready! Ask questions in natural language (type 'exit' to quit)\n")

while True:
    question = input("Your question: ").strip()
    if question.lower() in ["exit", "quit", "q"]:
        break

    try:
        result = chain.invoke({"question": question})
        print("\n📝 Answer:")
        print(result["result"])

        # Optional: show the Cypher that was generated
        if "intermediate_steps" in result:
            cypher = result["intermediate_steps"][0]["query"]
            print(f"\n🔍 Generated Cypher:\n{cypher}")

    except Exception as e:
        print(f"❌ Error: {e}")

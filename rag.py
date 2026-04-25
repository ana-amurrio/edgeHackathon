"""
Neo4j → Context Formatter → Claude API  (Graph RAG Pipeline)
─────────────────────────────────────────────────────────────
Flow:
  1. User asks a natural-language question
  2. Claude generates a Cypher query from the question
  3. Cypher query fetches relevant subgraph from Neo4j
  4. graph_to_text() converts it to a plain-text narrative
  5. Claude answers the question grounded in that context
"""

import os
import anthropic
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


# ════════════════════════════════════════════════════════════════
# 1.  CONTEXT FORMATTER
# ════════════════════════════════════════════════════════════════

def format_node(node) -> str:
    labels  = ", ".join(node.labels) if node.labels else "Entity"
    props   = dict(node)
    name    = props.get("code") or props.get("name") or props.get("title") or f"[{labels}]"
    details = {k: v for k, v in props.items() if k not in ("code",) and v is not None}
    if details:
        return f"{name} is a {labels} with {'; '.join(f'{k}: {v}' for k, v in details.items())}."
    return f"{name} is a {labels}."


def format_relationship(rel, start_node, end_node) -> str:
    rel_type   = rel.type.replace("_", " ").lower()
    start_name = start_node.get("code") or start_node.get("name") or f"[{', '.join(start_node.labels)}]"
    end_name   = end_node.get("code")   or end_node.get("name")   or f"[{', '.join(end_node.labels)}]"
    props      = dict(rel)
    prop_str   = f" ({', '.join(f'{k}: {v}' for k, v in props.items())})" if props else ""
    return f"{start_name} {rel_type} {end_name}{prop_str}."


def graph_to_text(records) -> str:
    seen_nodes, seen_rels, node_index = {}, {}, {}

    for record in records:
        for key in record.keys():
            value = record[key]
            if hasattr(value, "labels"):
                eid = value.element_id
                if eid not in seen_nodes:
                    seen_nodes[eid] = format_node(value)
                    node_index[eid] = value
            elif hasattr(value, "type") and hasattr(value, "start_node") and hasattr(value, "end_node"):
                eid = value.element_id
                if eid not in seen_rels:
                    start, end = value.start_node, value.end_node
                    for n in (start, end):
                        if n.element_id not in seen_nodes:
                            seen_nodes[n.element_id] = format_node(n)
                            node_index[n.element_id] = n
                    seen_rels[eid] = format_relationship(value, start, end)

    sections = []
    if seen_nodes:
        sections.append("Entities:\n" + "\n".join(f"- {s}" for s in seen_nodes.values()))
    if seen_rels:
        sections.append("Relationships:\n" + "\n".join(f"- {s}" for s in seen_rels.values()))
    return "\n\n".join(sections) if sections else "No graph data found."

class GraphContextFormatter:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query_to_text(self, cypher: str, params: dict = None) -> str:
        with self.driver.session() as session:
            records = list(session.run(cypher, params or {}))
        return graph_to_text(records)



SCHEMA = """
Node labels and properties:
  - Course (code, title, units, level, department, description)

Relationship types and properties:
  - (:Course)-[:REQUIRES {required: true/false}]->(:Course)
    meaning: the first course REQUIRES the second course as a prerequisite.
    required=true  → hard prerequisite (must be completed)
    required=false → recommended but not mandatory

Rules:
  - Always RETURN n, r, m — never omit the relationship variable r.
  - Use the `code` property to filter by course code (e.g. WHERE n.code = "BUS1 170").
  - To find what a student qualifies for, find courses whose prerequisites match completed courses.
  - To find what blocks a student, find REQUIRES relationships where the prereq has NOT been completed.
  - Do not use LIMIT unless asked.
"""

SYSTEM_PROMPT = """\
You are a helpful academic advisor assistant that answers questions about courses and prerequisites.
You will be given a plain-text summary of course nodes and prerequisite relationships from a Neo4j graph.
Base your answer strictly on this context.

When answering:
- Distinguish between required (hard) and recommended (optional) prerequisites.
- If a student lists completed courses, check each prerequisite against that list.
- Clearly state which courses they qualify for and which are blocked and why.
- If the context doesn't contain enough information, say so clearly.
Do not hallucinate facts that aren't in the context."""

CYPHER_PROMPT = f"""You are a Neo4j expert helping with a course prerequisite system.
Convert the user's question into a Cypher query.
Only return the raw Cypher query — no explanation, no markdown, no backticks.
Use this schema:
{SCHEMA}"""



class GraphRAGPipeline:
    """
    End-to-end pipeline:
      question → generate Cypher → Neo4j → plain text → Claude → answer
    """

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        anthropic_api_key: str = None,
        model: str = "claude-sonnet-4-6",
    ):
        self.graph   = GraphContextFormatter(neo4j_uri, neo4j_user, neo4j_password)
        self.claude  = anthropic.Anthropic(api_key=anthropic_api_key or os.environ["ANTHROPIC_API_KEY"])
        self.model   = model
        self.history = []

    def close(self):
        self.graph.close()

    def reset_history(self):
        """Clear conversation history to start a fresh session."""
        self.history = []

    def generate_cypher(self, question: str) -> str:
        """Use Claude to convert a natural-language question into a Cypher query."""
        response = self.claude.messages.create(
            model=self.model,
            max_tokens=512,
            system=CYPHER_PROMPT,
            messages=[{"role": "user", "content": question}]
        )
        cypher = response.content[0].text.strip()
        cypher = cypher.replace("```cypher", "").replace("```", "").strip()
        return cypher

    def ask(self, question: str, cypher: str = None, cypher_params: dict = None) -> str:
        """
        Ask a question grounded in graph context.
        If no Cypher is provided, one is auto-generated from the question.
        """
        # generate Cypher if not provided
        if cypher is None:
            cypher = self.generate_cypher(question)

        print("\n── Generated Cypher ───────────────────────────")
        print(cypher)

        # fetch & format graph context
        context = self.graph.query_to_text(cypher, cypher_params)

        print("\n── Graph Context ──────────────────────────────")
        print(context)
        print("───────────────────────────────────────────────\n")

        # build the user message
        user_message = (
            f"Here is the relevant knowledge graph context:\n\n"
            f"{context}\n\n"
            f"Question: {question}"
        )

        # maintain conversation history
        self.history.append({"role": "user", "content": user_message})

        # call Claude
        response = self.claude.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=self.history,
        )
        answer = response.content[0].text

        # store assistant reply in history
        self.history.append({"role": "assistant", "content": answer})

        return answer

    def ask_about(self, question: str, label: str = None, limit: int = 30) -> str:
        """Auto-builds a broad Cypher query fetching all nodes and relationships."""
        if label:
            cypher = f"MATCH (n:{label})-[r]->(m) RETURN n, r, m LIMIT {limit}"
        else:
            cypher = f"MATCH (n)-[r]->(m) RETURN n, r, m LIMIT {limit}"
        return self.ask(question, cypher)


# ════════════════════════════════════════════════════════════════
# 5.  EXAMPLE USAGE
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pipeline = GraphRAGPipeline(
        neo4j_uri      = os.getenv("NEO4J_URI",      "bolt://localhost:7687"),
        neo4j_user     = os.getenv("NEO4J_USER",     "neo4j"),
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password"),
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY"),
    )

    # Example A: what can a student take next?
    answer = pipeline.ask(
        "I have completed ENGL 1A, BUS3 12, and BUS1 20. What courses can I take next?"
    )
    print("Answer A:\n", answer)

    # Example B: what is blocking a student?
    answer2 = pipeline.ask(
        "I want to take BUS3 189. What prerequisites am I missing if I've only completed BUS2 130?"
    )
    print("\nAnswer B:\n", answer2)

    # Example C: full prereq chain
    answer3 = pipeline.ask(
        "What is the full prerequisite chain for BUS4 119A?"
    )
    print("\nAnswer C:\n", answer3)

    pipeline.close()
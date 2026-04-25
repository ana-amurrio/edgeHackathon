import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

import os
from dotenv import load_dotenv

load_dotenv("/Users/saranyavaitheeswaran/Downloads/.env", override=True)

print("URI:", os.getenv("NEO4J_URI"))
print("USER:", os.getenv("NEO4J_USERNAME"))
print("PASSWORD:", os.getenv("NEO4J_PASSWORD"))


"""
SmartPlan Neo4j Loader
======================
Loads SJSU course catalog data into Neo4j Aura for the SmartPlan academic advising app.

Graph schema:
  Nodes:   Course, Requirement, Misconception
  Edges:   PREREQUISITE_OF, SATISFIES, RELATED_TO

Usage:
  1. Set your Neo4j Aura credentials in the config block below (or use env vars).
  2. Place your CSV files in the same directory or update CSV_DIR.
  3. Run: python smartplan_loader.py

CSV files expected:
  courses.csv         - Course nodes
  prerequisites.csv   - PREREQUISITE_OF edges
  satisfies.csv       - SATISFIES edges (course → requirement)
  misconceptions.csv  - Misconception nodes + RELATED_TO edges
"""

import csv
import os
from pathlib import Path
from neo4j import GraphDatabase

# ─── CONFIG ──────────────────────────────────────────────────────────────────
# Use environment variables (recommended) or paste credentials directly for dev.

NEO4J_URI      = os.getenv("NEO4J_URI",      "neo4j+s://<your-aura-id>.databases.neo4j.io")
NEO4J_USER     = os.getenv("NEO4J_USERNAME",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "<your-password>")

CSV_DIR = Path("/Users/saranyavaitheeswaran/Downloads/data")  # folder containing the 4 CSV files

# ─── CONNECTION ───────────────────────────────────────────────────────────────

def get_driver():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("✅ Connected to Neo4j Aura")
    return driver


# ─── SCHEMA / CONSTRAINTS ────────────────────────────────────────────────────

def create_constraints(session):
    """Unique constraints so re-runs are idempotent."""
    constraints = [
        "CREATE CONSTRAINT course_code IF NOT EXISTS FOR (c:Course) REQUIRE c.course_code IS UNIQUE",
        "CREATE CONSTRAINT requirement_key IF NOT EXISTS FOR (r:Requirement) REQUIRE (r.name, r.program) IS NODE KEY",
        "CREATE CONSTRAINT misconception_id IF NOT EXISTS FOR (m:Misconception) REQUIRE m.misconception_id IS UNIQUE",
    ]
    for cypher in constraints:
        session.run(cypher)
    print("✅ Constraints created")


# ─── NODE LOADERS ────────────────────────────────────────────────────────────

def load_courses(session, csv_path: Path):
    """
    Expects columns: course_code, title, units, level, department, description
    Swap in your own CSV with the same headers to load real catalog data.
    """
    rows = _read_csv(csv_path)
    cypher = """
    UNWIND $rows AS row
    MERGE (c:Course {course_code: row.course_code})
    SET c.title       = row.title,
        c.units       = toInteger(row.units),
        c.level       = row.level,
        c.department  = row.department,
        c.description = row.description
    """
    session.run(cypher, rows=rows)
    print(f"✅ Loaded {len(rows)} courses")


def load_misconceptions(session, csv_path: Path):
    """
    Expects columns: misconception_id, misconception_text, correct_answer,
                     related_course, category
    Also creates RELATED_TO edge to the Course node.
    """
    rows = _read_csv(csv_path)
    cypher = """
    UNWIND $rows AS row
    MERGE (m:Misconception {misconception_id: row.misconception_id})
    SET m.text         = row.misconception_text,
        m.correct      = row.correct_answer,
        m.category     = row.category
    WITH m, row
    MATCH (c:Course {course_code: row.related_course})
    MERGE (m)-[:RELATED_TO]->(c)
    """
    session.run(cypher, rows=rows)
    print(f"✅ Loaded {len(rows)} misconceptions with RELATED_TO edges")


# ─── RELATIONSHIP LOADERS ────────────────────────────────────────────────────

def load_prerequisites(session, csv_path: Path):
    """
    Expects columns: course_code, prerequisite_code, required (true/false)
    Creates: (prerequisite)-[:PREREQUISITE_OF]->(course)
    Direction chosen so traversal reads naturally:
      "DAT 210 is a PREREQUISITE_OF DAT 226"
    """
    rows = _read_csv(csv_path)
    cypher = """
    UNWIND $rows AS row
    MATCH (prereq:Course {course_code: row.prerequisite_code})
    MATCH (course:Course  {course_code: row.course_code})
    MERGE (prereq)-[r:PREREQUISITE_OF]->(course)
    SET r.required = (row.required = 'true')
    """
    session.run(cypher, rows=rows)
    print(f"✅ Loaded {len(rows)} PREREQUISITE_OF edges")


def load_satisfies(session, csv_path: Path):
    """
    Expects columns: course_code, requirement, program
    Creates Requirement nodes and SATISFIES edges:
      (course)-[:SATISFIES]->(requirement)
    """
    rows = _read_csv(csv_path)
    cypher = """
    UNWIND $rows AS row
    MATCH (c:Course {course_code: row.course_code})
    MERGE (r:Requirement {name: row.requirement, program: row.program})
    MERGE (c)-[:SATISFIES]->(r)
    """
    session.run(cypher, rows=rows)
    print(f"✅ Loaded {len(rows)} SATISFIES edges")


# ─── VERIFICATION QUERIES ────────────────────────────────────────────────────

def verify(session):
    counts = {
        "Course nodes":          "MATCH (c:Course) RETURN count(c) AS n",
        "Requirement nodes":     "MATCH (r:Requirement) RETURN count(r) AS n",
        "Misconception nodes":   "MATCH (m:Misconception) RETURN count(m) AS n",
        "PREREQUISITE_OF edges": "MATCH ()-[r:PREREQUISITE_OF]->() RETURN count(r) AS n",
        "SATISFIES edges":       "MATCH ()-[r:SATISFIES]->() RETURN count(r) AS n",
        "RELATED_TO edges":      "MATCH ()-[r:RELATED_TO]->() RETURN count(r) AS n",
    }
    print("\n📊 Graph summary:")
    for label, cypher in counts.items():
        result = session.run(cypher).single()
        print(f"   {label}: {result['n']}")

    # Sample: prerequisites for DAT 226
    print("\n🔍 Sample — prerequisites for DAT 226:")
    result = session.run("""
        MATCH (prereq:Course)-[r:PREREQUISITE_OF]->(c:Course {course_code: 'DAT 226'})
        RETURN prereq.course_code AS prereq, r.required AS required
    """)
    for rec in result:
        req_flag = "required" if rec["required"] else "recommended"
        print(f"   {rec['prereq']} ({req_flag})")

    # Sample: misconceptions related to DAT 299
    print("\n🔍 Sample — misconceptions related to DAT 299:")
    result = session.run("""
        MATCH (m:Misconception)-[:RELATED_TO]->(c:Course {course_code: 'DAT 299'})
        RETURN m.text AS misconception, m.correct AS correction
    """)
    for rec in result:
        print(f"   ❌ {rec['misconception']}")
        print(f"   ✅ {rec['correction']}")


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def clear_graph(session):
    """⚠️  Wipes all nodes and edges. Use only during dev/reset."""
    session.run("MATCH (n) DETACH DELETE n")
    print("🗑️  Graph cleared")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    driver = get_driver()

    with driver.session() as session:
        # Optional: uncomment to reset graph before each load during dev
        # clear_graph(session)

        create_constraints(session)

        load_courses(session,       CSV_DIR / "courses.csv")
        load_misconceptions(session, CSV_DIR / "misconceptions.csv")
        load_prerequisites(session,  CSV_DIR / "prerequisites.csv")
        load_satisfies(session,      CSV_DIR / "satisfies.csv")

        verify(session)

    driver.close()
    print("\n✅ Done — graph ready for SmartPlan queries")


if __name__ == "__main__":
    main()
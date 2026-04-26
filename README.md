# edgeHackathon
# 🎓 SmartPlan - SJSU Academic Advising AI Agent

**SmartPlan** is a conversational AI-powered academic advising system designed to help San José State University (SJSU) students navigate their degree requirements, understand course prerequisites, and plan their academic journey.

## Overview

SmartPlan leverages a **Graph RAG (Retrieval-Augmented Generation)** architecture to deliver accurate, context-aware academic advising. The system combines:

- **Neo4j Graph Database**: Stores course catalog data, prerequisites, and degree requirements as a knowledge graph
- **Claude AI (Anthropic)**: Natural language understanding and generation for intelligent conversations
- **Streamlit**: User-friendly web interface for students to ask questions in plain English

## Features

✨ **Conversational Interface**: Ask natural language questions about courses and prerequisites  
📚 **Prerequisite Analysis**: Understand course dependencies and progression paths  
🎯 **Qualification Check**: Learn which courses you're eligible to take based on completed courses  
🔗 **Full Prerequisite Chains**: Explore complete prerequisite hierarchies for any course  
💾 **Conversation Memory**: Multi-turn conversations with persistent context  
🗑️ **Session Management**: Clear conversation history and reset chat state

## Quick Start

### Prerequisites

- Python 3.9+
- Neo4j Aura instance (cloud-hosted) or Neo4j Desktop/Server
- Anthropic API key (Claude access)
- Git

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ReetiShah/edgeHackathon.git
   cd edgeHackathon
   ```

2. **Install dependencies**:
   ```bash
   pip install streamlit neo4j anthropic python-dotenv
   ```

3. **Configure environment variables**:
   Create a `.env` file in the project root:
   ```env
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

4. **Load your course data** (one-time setup):
   ```bash
   python loadNeo4j.py
   ```
   Ensure your CSV files are in the `data/` directory:
   - `courses.csv` - Course catalog
   - `prerequisites.csv` - Course prerequisites
   - `satisfies.csv` - Degree requirement mappings
   - `misconceptions.csv` - Common academic misconceptions

5. **Run the application**:
   ```bash
   streamlit run app.py
   ```
   Open your browser to `http://localhost:8501`

## Architecture

### System Components

#### 1. **app.py** - Streamlit Frontend
- Web interface for user interactions
- Chat message display and input handling
- Session state management for conversations
- Control panel for resetting chat history

#### 2. **rag.py** - Graph RAG Pipeline
Core intelligence system with three stages:

**Stage 1: Cypher Generation**
- Claude converts natural language questions to Neo4j Cypher queries
- Uses schema and rules to generate accurate graph queries

**Stage 2: Graph Context Retrieval**
- Executes Cypher query against Neo4j
- Formats graph data (nodes and relationships) into natural language context

**Stage 3: Answer Generation**
- Claude combines user question + graph context to generate grounded answers
- Maintains conversation history for multi-turn interactions

#### 3. **loadNeo4j.py** - Data Loader
- Imports course catalog from CSV files
- Creates graph schema with constraints
- Establishes relationships (prerequisites, requirements)
- Provides verification queries

### Data Model

**Nodes**:
- `Course` - Course entity with properties: code, title, units, level, department, description
- `Requirement` - Degree requirements
- `Misconception` - Common academic misconceptions

**Relationships**:
- `REQUIRES` - Prerequisite relationship (Course A → Course B means A must be completed before B)
- `SATISFIES` - Course satisfies a degree requirement

## Example Usage

### Question Examples

Try asking SmartPlan questions like:

- *"I've completed ENGL 1A. What's next?"*
- *"What do I need before BUS3 189?"*
- *"What is the full prerequisite chain for BUS4 119A?"*
- *"I have BUS1 20 and BUS2 90. Am I blocked from BUS1 170?"*

### Running Standalone Scripts

```bash
# Test the RAG pipeline directly
python rag.py

# Verify database connection and schema
python loadNeo4j.py

# Check streaming functionality
python streamCheck.py
```

## Data Format

### courses.csv
```csv
course_code,title,units,level,department,description
BUS1 20,Intro to Business,3,Lower,Business,Introduction to business principles
BUS3 189,Advanced Management,3,Upper,Business,Advanced management concepts
```

### prerequisites.csv
```csv
course_code,prerequisite_code,required
BUS3 189,BUS1 20,true
BUS3 189,BUS2 90,false
```

### satisfies.csv
```csv
course_code,requirement,program
BUS1 20,Core Business Requirement,BS Business
BUS3 189,Upper Division Elective,BS Business
```

## Configuration

Edit `.env` to customize:
- **NEO4J_URI**: Neo4j connection string
- **NEO4J_USER**: Database username
- **NEO4J_PASSWORD**: Database password
- **ANTHROPIC_API_KEY**: Claude API key

## Project Structure

```
edgeHackathon/
├── app.py                 # Streamlit web interface
├── rag.py                 # Graph RAG pipeline logic
├── loadNeo4j.py          # Data loader script
├── seeding.py            # Data seeding utilities
├── streamCheck.py        # Streaming validation
├── data/                 # CSV data files
│   ├── courses.csv
│   ├── prerequisites.csv
│   ├── satisfies.csv
│   └── misconceptions.csv
├── .env                  # Environment variables (create this)
└── README.md            # This file
```

## Technologies Used

- **Streamlit**: Web framework for ML apps
- **Neo4j**: Graph database for knowledge representation
- **Claude (Anthropic)**: Large language model for NLP
- **Python**: Core programming language
- **Cypher**: Graph query language

## Development

### Adding New Features

1. **New question types**: Update `SCHEMA` and `SYSTEM_PROMPT` in `rag.py`
2. **New data sources**: Extend `loadNeo4j.py` with additional CSV loaders
3. **UI enhancements**: Modify `app.py` to add Streamlit components

### Debugging

Enable debug output by running:
```bash
streamlit run app.py --logger.level=debug
```

The RAG pipeline prints generated Cypher queries and graph context for troubleshooting.

## Performance Optimization

- **Graph Indexing**: Create Neo4j indexes on frequently queried properties
- **Query Caching**: Cache Cypher generation results for common questions
- **Batch Loading**: Use bulk imports for large CSV files

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Verify Neo4j URI and credentials in `.env` |
| "No context found" | Check that CSV data is loaded with `python loadNeo4j.py` |
| API key errors | Ensure `ANTHROPIC_API_KEY` is set and valid |
| Slow responses | Check Neo4j database indexes; consider reducing query scope |

## Future Enhancements

- 📊 Add visualization of prerequisite dependency graphs
- 🔄 Support for dynamic course catalog updates
- 📱 Mobile app version
- 🌐 Multi-language support
- 📈 Analytics dashboard for advising patterns

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


## Contact & Support

For questions or issues, please open a GitHub issue or contact the development team.

---

**Built for SJSU Students** 🎓 | *Helping you plan your academic journey one question at a time*

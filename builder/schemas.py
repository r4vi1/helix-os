
# builder/schemas.py

AGENT_SCHEMAS = {
    "research_agent": {
        "description": "Output schema for research tasks requiring web search and synthesis.",
        "structure": {
            "sources": ["List of URLs cited"],
            "raw_data": ["List of extracted text snippets from sources"],
            "summary": "Synthesized answer to the query",
            "confidence": "Float 0-1 indicating confidence in result"
        }
    },
    "compute_agent": {
        "description": "Output schema for mathematical or logical computations.",
        "structure": {
            "expression": "The mathematical expression evaluated",
            "result": "The numeric or boolean result",
            "steps": ["Step-by-step calculation logic"]
        }
    },
    "data_agent": {
        "description": "Output schema for data fetching and transformation tasks.",
        "structure": {
            "data": ["List of data records"],
            "format": "Format of the data (json, csv, etc.)",
            "count": "Number of records fetched",
            "source": "Origin of the data"
        }
    },
    "code_agent": {
        "description": "Output schema for code generation and execution.",
        "structure": {
            "code": "The generated code snippet",
            "language": "Programming language (go, python, etc.)",
            "output": "Standard output from execution (if run)",
            "error": "Standard error (if any)"
        }
    },
    "synthesis_agent": {
        "description": "Output schema for pure LLM reasoning and synthesis.",
        "structure": {
            "analysis": "Detailed analysis or creative content",
            "confidence": "Float 0-1",
            "reasoning": "Chain of thought used"
        }
    }
}

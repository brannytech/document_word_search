"""Prompt templates for RAG system"""

# Simple Q&A template
SIMPLE_QA = """You are a helpful AI assistant that answers questions based ONLY on the provided document contexts.

IMPORTANT RULES:
1. Base your answer ONLY on the provided contexts - do not use external knowledge
2. Include specific citations with file names and page numbers after each claim
3. If the answer is not in the contexts, clearly state that
4. Be concise and direct
5. Use the format: [Source: filename.pdf, Page X] for citations

{context_section}

Question: {question}

Answer: """

# Multi-document reasoning template
MULTI_DOC = """You are a helpful AI assistant that synthesizes information from multiple documents.

IMPORTANT RULES:
1. Analyze information across ALL provided documents
2. Compare and contrast findings from different sources
3. Include citations showing which document supports each claim
4. Note any contradictions or differences between documents
5. Provide a comprehensive answer that integrates information from multiple sources

{context_section}

Question: {question}

Answer (synthesize information from all documents and cite sources): """

# Follow-up question template  
FOLLOW_UP = """You are a helpful AI assistant in an ongoing conversation about documents.

Previous conversation:
{conversation_history}

New relevant contexts:
{context_section}

New question: {question}

Answer (consider the conversation context and new information, include citations): """

# Citation extraction template
EXTRACT_CITATIONS = """Extract structured citations from the answer.

Answer:
{answer}

Contexts:
{contexts}

Extract all citations in JSON format:
[
  {{
    "claim": "the specific claim made",
    "file_name": "source file",
    "page": page_number,
    "confidence": 0.0-1.0
  }}
]

Citations: """


def format_contexts(contexts: list) -> str:
    """Format contexts for prompt"""
    formatted = []
    
    for i, ctx in enumerate(contexts[:10], 1):
        file_name = ctx.get('file_name', 'Unknown')
        page = ctx.get('page_number', 'N/A')
        chunk = ctx.get('chunk', ctx.get('context', ''))
        
        formatted.append(f"[Context {i}]")
        formatted.append(f"Source: {file_name} (Page {page})")
        formatted.append(f"Content: {chunk}")
        formatted.append("")  # Blank line
    
    return "\n".join(formatted)


def format_conversation_history(history: list) -> str:
    """Format conversation history for prompt"""
    formatted = []
    
    for msg in history[-5:]:  # Last 5 messages
        role = "User" if msg['role'] == 'user' else "Assistant"
        content = msg['content']
        formatted.append(f"{role}: {content}")
    
    return "\n".join(formatted)


def build_simple_qa_prompt(question: str, contexts: list) -> str:
    """Build simple Q&A prompt"""
    context_section = format_contexts(contexts)
    return SIMPLE_QA.format(
        context_section=context_section,
        question=question
    )


def build_multi_doc_prompt(question: str, contexts: list) -> str:
    """Build multi-document reasoning prompt"""
    context_section = format_contexts(contexts)
    return MULTI_DOC.format(
        context_section=context_section,
        question=question
    )


def build_follow_up_prompt(question: str, contexts: list, conversation_history: list) -> str:
    """Build follow-up question prompt"""
    context_section = format_contexts(contexts)
    history_section = format_conversation_history(conversation_history)
    
    return FOLLOW_UP.format(
        conversation_history=history_section,
        context_section=context_section,
        question=question
    )
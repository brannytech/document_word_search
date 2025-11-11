"""Prompt templates for RAG system"""

# System instruction for all prompts
SYSTEM_INSTRUCTION = """You are a helpful AI assistant that answers questions based ONLY on the provided document contexts.

IMPORTANT RULES:
1. Base your answer ONLY on the provided contexts - do not use external knowledge
2. Include specific citations with file names and page numbers after each claim
3. If the answer is not in the contexts, clearly state that
4. Be concise and direct
5. Use the format: [Source: filename, Page X] for citations
"""


def build_simple_prompt(question: str, contexts: list) -> str:
    """Build simple Q&A prompt"""
    
    prompt_parts = [SYSTEM_INSTRUCTION, "\n"]
    
    # Add document contexts
    prompt_parts.append("Relevant document contexts:\n\n")
    
    for i, ctx in enumerate(contexts[:10], 1):  # Limit to top 10
        file_name = ctx.get('file_name', 'Unknown')
        page = ctx.get('page_number', 'N/A')
        chunk = ctx.get('chunk', ctx.get('context', ''))
        
        prompt_parts.append(f"[Context {i}]\n")
        prompt_parts.append(f"Source: {file_name} (Page {page})\n")
        prompt_parts.append(f"Content: {chunk}\n\n")
    
    # Add question
    prompt_parts.append(f"Question: {question}\n\n")
    
    # Add instruction for answer
    prompt_parts.append(
        "Answer: Based on the above contexts, provide a detailed answer. "
        "Include citations in the format [Source: filename, Page X] after each claim.\n\n"
    )
    
    return ''.join(prompt_parts)


def build_followup_prompt(question: str, contexts: list, conversation_history: list) -> str:
    """Build follow-up question prompt with conversation history"""
    
    prompt_parts = [SYSTEM_INSTRUCTION, "\n"]
    
    # Add conversation history if present
    if conversation_history:
        prompt_parts.append("Previous conversation:\n")
        for msg in conversation_history[-5:]:  # Last 5 messages
            role = msg['role'].capitalize()
            content = msg['content']
            prompt_parts.append(f"{role}: {content}\n")
        prompt_parts.append("\n")
    
    # Add new contexts
    prompt_parts.append("New relevant contexts:\n\n")
    
    for i, ctx in enumerate(contexts[:10], 1):
        file_name = ctx.get('file_name', 'Unknown')
        page = ctx.get('page_number', 'N/A')
        chunk = ctx.get('chunk', ctx.get('context', ''))
        
        prompt_parts.append(f"[Context {i}]\n")
        prompt_parts.append(f"Source: {file_name} (Page {page})\n")
        prompt_parts.append(f"Content: {chunk}\n\n")
    
    # Add new question
    prompt_parts.append(f"New question: {question}\n\n")
    
    # Add instruction
    prompt_parts.append(
        "Answer: Consider the conversation context and the new information. "
        "Include citations in the format [Source: filename, Page X].\n\n"
    )
    
    return ''.join(prompt_parts)


def build_multi_doc_prompt(question: str, contexts: list) -> str:
    """Build multi-document reasoning prompt"""
    
    prompt_parts = [SYSTEM_INSTRUCTION, "\n"]
    
    prompt_parts.append(
        "TASK: Synthesize information from multiple documents.\n"
        "- Compare and contrast findings from different sources\n"
        "- Note any contradictions or differences\n"
        "- Provide a comprehensive answer integrating multiple sources\n\n"
    )
    
    # Group contexts by document
    by_doc = {}
    for ctx in contexts:
        file_name = ctx.get('file_name', 'Unknown')
        if file_name not in by_doc:
            by_doc[file_name] = []
        by_doc[file_name].append(ctx)
    
    # Add contexts grouped by document
    prompt_parts.append("Document contexts:\n\n")
    
    for doc_name, doc_contexts in by_doc.items():
        prompt_parts.append(f"=== {doc_name} ===\n")
        for i, ctx in enumerate(doc_contexts[:3], 1):  # Top 3 per doc
            page = ctx.get('page_number', 'N/A')
            chunk = ctx.get('chunk', ctx.get('context', ''))
            prompt_parts.append(f"[Excerpt {i}, Page {page}]\n{chunk}\n\n")
        prompt_parts.append("\n")
    
    # Add question
    prompt_parts.append(f"Question: {question}\n\n")
    
    # Add instruction
    prompt_parts.append(
        "Answer: Synthesize information from all documents. "
        "Compare findings and cite sources: [Source: filename, Page X].\n\n"
    )
    
    return ''.join(prompt_parts)


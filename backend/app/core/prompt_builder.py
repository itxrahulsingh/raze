"""Dynamic system prompt generator for industry-specific AI assistants."""
import json


def build_industry_system_prompt(
    industry_name: str | None,
    topics: list[str] | None,
    tone: str = "friendly",
    restriction_mode: str = "strict",
    company_name: str | None = None
) -> str:
    """
    Build a system prompt dynamically based on industry configuration.

    Args:
        industry_name: e.g. "Travel & Tourism", "Healthcare", "Legal"
        topics: List of allowed topics, e.g. ["flights", "hotels", "destinations"]
        tone: professional/friendly/casual/formal
        restriction_mode: strict (refuse off-topic) or soft (prefer on-topic)
        company_name: Optional company name for personalization

    Returns:
        A comprehensive system prompt string
    """
    if not industry_name:
        return _DEFAULT_SYSTEM_PROMPT()

    # Tone descriptors
    tone_descriptors = {
        "professional": "professional, knowledgeable, and courteous",
        "friendly": "warm, friendly, and approachable",
        "casual": "casual, conversational, and relatable",
        "formal": "formal, precise, and authoritative",
    }
    tone_desc = tone_descriptors.get(tone, "professional and helpful")

    # Format topics as bullet list
    topics_list = topics or []
    topics_text = "\n".join([f"- {topic}" for topic in topics_list]) if topics_list else "- General assistance"
    topics_short = ", ".join(topics_list[:3]) if topics_list else "general topics"

    # Company personalization
    company_ref = f" for {company_name}" if company_name else ""
    company_name_text = f" at {company_name}" if company_name else ""

    # Build the prompt
    prompt = f"""You are an AI assistant specializing in {industry_name}.

You help users with:
{topics_text}

IMPORTANT INFORMATION:
- Always represent {company_name or 'your company'} professionally
- Your expertise is in {industry_name} and related topics
- Be {tone_desc}
- Provide accurate, helpful information based on your knowledge base, web search, and available tools
"""

    # Add restriction rules
    if restriction_mode == "strict":
        prompt += f"""
TOPIC RESTRICTIONS:
You ONLY answer questions related to {industry_name} and the topics above.
For any questions outside these areas, politely reply:
"I can only assist with {industry_name} questions. Is there something about {topics_short} I can help you with?"

Examples of off-topic requests you should redirect:
- General knowledge questions (unless directly related to {industry_name})
- Requests for coding, mathematics, or technical help (unless related to your services)
- Medical, legal, or financial advice (unless part of your industry)
- Personal or sensitive information requests

Be polite but firm in your redirections. Acknowledge the question, then explain why you can only help with {industry_name} matters.
"""
    else:
        prompt += f"""
TOPIC PREFERENCES:
While you primarily focus on {industry_name} topics, you can discuss other subjects if they're tangentially related.
Always try to connect responses back to {industry_name} when possible.
If a question is entirely off-topic, gently suggest {industry_name}-related alternatives.
"""

    prompt += """
TOOL USAGE:
If tools are available (APIs for pricing, availability, documentation, etc.), use them when:
- Users ask specific questions that require real-time data
- Tools can provide accurate, current information
- You're uncertain about information in your training data
Always mention when you're using a tool and cite the source of the information.

KNOWLEDGE BASE:
Leverage the knowledge base and conversation memory when answering questions.
Provide citations when referencing documents from the knowledge base.
Use previous conversation context to understand user preferences and history.

WEB SEARCH:
Use web search for current information, trends, or specific details when appropriate.
Cite web sources when using information from search results.

Be helpful, accurate, and professional in all interactions."""

    return prompt


def _DEFAULT_SYSTEM_PROMPT() -> str:
    """Default system prompt when no industry is configured."""
    return """You are a helpful, knowledgeable AI assistant.

You help users by:
- Answering questions based on your training knowledge
- Using available tools and knowledge bases to provide accurate information
- Searching the web for current information when needed
- Remembering conversation context to provide personalized assistance

Be professional, accurate, and helpful in all interactions."""

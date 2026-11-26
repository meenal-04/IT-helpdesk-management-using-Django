"""
AI assistance using OmniRouter's OpenAI-compatible API.
"""

import os
import json
import requests
from django.conf import settings


def _build_prompt(ticket, conversation=None):
    """Build the analysis prompt for the AI."""
    conversation = conversation or []
    conv_text = ""
    if conversation:
        conv_text = "\n\nPrevious conversation:\n" + "\n".join(
            f"- {author}: {msg}" for author, msg in conversation[-10:]
        )

    return f"""You are an IT helpdesk assistant. Analyze this support ticket and provide helpful guidance to the IT support staff.

Ticket ID: #{ticket.id}
Subject: {ticket.subject}
Category: {ticket.category.name if ticket.category else 'Uncategorized'}
Priority: {ticket.get_priority_display()}
Status: {ticket.get_status_display()}
Description: {ticket.description}{conv_text}

Respond ONLY with a valid JSON object (no markdown, no code fences) in this exact structure:
{{
  "possible_cause": "One or two sentences on the most likely cause.",
  "troubleshooting_steps": ["Step 1", "Step 2", "Step 3"],
  "recommended_action": "What the support staff should do next.",
  "suggested_priority": "low|medium|high|critical",
  "suggested_category": "Hardware|Software|Network|Email|Account/Login|Printer|Security|Other",
  "suggested_response": "A polite reply the support staff can send to the employee."
}}"""


def get_ai_assistance(ticket, conversation=None):
    """
    Call OmniRouter. Returns a dict:
      - On success: {'possible_cause': ..., 'troubleshooting_steps': [...], ...}
      - On failure: {'error': 'human-friendly message'}
    Never raises — always returns a dict.
    """
    api_key = os.getenv("OMNI_API_KEY", "").strip()
    if not api_key:
        return {"error": "AI assistance is temporarily unavailable. (API key not configured.)"}

    model = getattr(settings, "OMNI_MODEL", "auto")
    base_url = getattr(settings, "OMNI_BASE_URL", "https://api.omnilabs.ai/v1")
    url = f"{base_url.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful IT support assistant. Reply with valid JSON only."},
            {"role": "user", "content": _build_prompt(ticket, conversation)},
        ],
        "temperature": 0.4,
        "max_tokens": 900,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.exceptions.Timeout:
        return {"error": "AI assistance is temporarily unavailable. (Request timed out.)"}
    except requests.exceptions.RequestException:
        return {"error": "AI assistance is temporarily unavailable. (Network error.)"}

    if response.status_code == 401:
        return {"error": "AI assistance is temporarily unavailable. (Invalid API key.)"}
    if response.status_code == 429:
        return {"error": "AI assistance is temporarily unavailable. (Rate limit reached.)"}
    if response.status_code >= 500:
        return {"error": "AI assistance is temporarily unavailable. (Provider error.)"}
    if response.status_code != 200:
        return {"error": f"AI assistance is temporarily unavailable. (HTTP {response.status_code})"}

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError):
        return {"error": "AI assistance is temporarily unavailable. (Unexpected response.)"}

    # Strip markdown code fences if the model wrapped the JSON
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {
            "possible_cause": "See raw AI output below.",
            "troubleshooting_steps": [],
            "recommended_action": "",
            "suggested_priority": "",
            "suggested_category": "",
            "suggested_response": content,
        }

    return {
        "possible_cause": parsed.get("possible_cause", ""),
        "troubleshooting_steps": parsed.get("troubleshooting_steps", []) or [],
        "recommended_action": parsed.get("recommended_action", ""),
        "suggested_priority": parsed.get("suggested_priority", ""),
        "suggested_category": parsed.get("suggested_category", ""),
        "suggested_response": parsed.get("suggested_response", ""),
    }
"""
WhatsApp Webhook Integration Router
===================================
Supports:
1. Meta WhatsApp Cloud API (Verification GET & Webhook Message POST)
2. Twilio WhatsApp Sandbox (Form data Body & From)
3. Direct API test payloads

Calls UrjaMind Agentic Copilot to generate verified, tool-grounded responses.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel
from agentic_copilot import ask_agentic_copilot

logger = logging.getLogger("urjamind.whatsapp")

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "urjamind_token_2026")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")


class DirectWhatsAppMessage(BaseModel):
    message: str
    from_number: Optional[str] = "+919876543210"


@router.get("/webhook")
async def verify_meta_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """
    Meta WhatsApp Cloud API Webhook Verification Endpoint.
    When configured in Meta App Dashboard, Meta sends a GET request with hub.challenge.
    """
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully with challenge: %s", hub_challenge)
        return Response(content=hub_challenge or "", media_type="text/plain")

    if hub_verify_token and hub_verify_token != WHATSAPP_VERIFY_TOKEN:
        raise HTTPException(status_code=403, detail="Verification token mismatch")

    return {
        "status": "active",
        "service": "UrjaMind WhatsApp Cloud Webhook",
        "usage": "Configure Meta Developer Portal Webhook Callback URL to this endpoint with verify token 'urjamind_token_2026'",
    }


@router.post("/webhook")
async def receive_whatsapp_message(request: Request):
    """
    Handles incoming messages from Meta WhatsApp Cloud API or Twilio Sandbox.
    Executes Agentic Copilot and responds with verified tool output.
    """
    content_type = request.headers.get("content-type", "")
    incoming_text = ""
    sender_number = "unknown"

    # 1. Handle Twilio Sandbox (application/x-www-form-urlencoded)
    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        incoming_text = str(form_data.get("Body", "")).strip()
        sender_number = str(form_data.get("From", "unknown"))

    # 2. Handle Meta WhatsApp Cloud API or Direct JSON
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        # Meta Cloud API payload format:
        # entry[0].changes[0].value.messages[0].text.body
        try:
            entry = payload.get("entry", [{}])[0]
            change = entry.get("changes", [{}])[0]
            value = change.get("value", {})
            messages = value.get("messages", [])
            if messages:
                msg = messages[0]
                sender_number = msg.get("from", "unknown")
                if msg.get("type") == "text":
                    incoming_text = msg.get("text", {}).get("body", "")
        except Exception:
            pass

        # Fallback to direct test or Twilio JSON payload: {"Body": "...", "message": "...", "text": "..."}
        if not incoming_text:
            incoming_text = str(payload.get("message") or payload.get("Body") or payload.get("text") or "").strip()
            sender_number = payload.get("from_number") or payload.get("From") or sender_number

    if not incoming_text:
        return {"status": "ignored", "reason": "No readable text content found in webhook"}

    logger.info("Incoming WhatsApp from %s: '%s'", sender_number, incoming_text)

    # Execute Agentic Copilot
    bot_response = ask_agentic_copilot(incoming_text)
    answer_text = bot_response.get("content", "Maaf kijiye, abhi process nahi ho paya.")

    # If outbound credentials exist, send message back via Meta Graph API
    if WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_ID and sender_number != "unknown":
        try:
            import requests
            url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages"
            headers = {
                "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            }
            body = {
                "messaging_product": "whatsapp",
                "to": sender_number,
                "type": "text",
                "text": {"body": answer_text},
            }
            requests.post(url, headers=headers, json=body, timeout=5)
        except Exception as e:
            logger.warning("Outbound WhatsApp dispatch error: %s", e)

    # Return response payload (also supports Twilio TwiML format if Twilio requested)
    if "application/x-www-form-urlencoded" in content_type:
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{answer_text}</Message>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    return {
        "status": "success",
        "sender": sender_number,
        "input_query": incoming_text,
        "bot_response": answer_text,
        "response": answer_text,
        "engine": bot_response.get("engine"),
        "tool_called": bot_response.get("tool_called"),
    }


@router.post("/test-chat")
async def test_whatsapp_chat(payload: DirectWhatsAppMessage):
    """Convenience endpoint to test WhatsApp copilot interaction directly."""
    response = ask_agentic_copilot(payload.message)
    return {
        "from": payload.from_number,
        "input": payload.message,
        "reply": response["content"],
        "tool_called": response.get("tool_called"),
        "engine": response.get("engine"),
    }

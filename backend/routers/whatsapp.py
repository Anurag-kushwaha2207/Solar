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

import base64
import hashlib
import hmac
import logging
import os
import re
import xml.sax.saxutils
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel
import httpx

from agentic_copilot import ask_agentic_copilot

logger = logging.getLogger("urjamind.whatsapp")

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "urjamind_token_2026")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN") or os.environ.get("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")
META_APP_SECRET = os.environ.get("META_APP_SECRET")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").lower()


def format_for_whatsapp(text: str) -> str:
    """
    Format standard markdown into WhatsApp-compatible text syntax.
    - Markdown **bold** -> WhatsApp *bold*
    - Ensure readable linebreaks
    """
    if not text:
        return ""
    # Convert **bold** to *bold*
    formatted = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)
    return formatted


def verify_meta_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """Verify X-Hub-Signature-256 for Meta WhatsApp Cloud API webhooks."""
    if not META_APP_SECRET:
        return True  # If no secret configured (development/testing), pass
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected_hash = hmac.new(META_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    received_hash = signature_header.split("sha256=")[-1]
    return hmac.compare_digest(expected_hash, received_hash)


def verify_twilio_signature(url: str, params: Dict[str, str], signature_header: Optional[str]) -> bool:
    """Verify X-Twilio-Signature for Twilio webhook requests."""
    if not TWILIO_AUTH_TOKEN:
        return True  # If no Twilio auth token configured, pass
    if not signature_header:
        return False
    # Standard Twilio signature calculation:
    # URL string + sorted parameter keys and values concatenated
    data_to_sign = url
    for key in sorted(params.keys()):
        data_to_sign += f"{key}{params[key]}"
    expected_mac = hmac.new(TWILIO_AUTH_TOKEN.encode("utf-8"), data_to_sign.encode("utf-8"), hashlib.sha1).digest()
    expected_sig = base64.b64encode(expected_mac).decode("utf-8")
    return hmac.compare_digest(expected_sig, signature_header)


class DirectWhatsAppMessage(BaseModel):
    message: str
    from_number: Optional[str] = "+919837101838"


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
        "verify_token_configured": bool(WHATSAPP_VERIFY_TOKEN),
        "usage": "Configure Meta Developer Portal Webhook Callback URL to this endpoint",
    }


@router.post("/webhook")
async def receive_whatsapp_message(request: Request):
    """
    Handles incoming messages from Meta WhatsApp Cloud API or Twilio Sandbox.
    Validates provider-specific signatures (Meta X-Hub-Signature or Twilio X-Twilio-Signature),
    executes Agentic Copilot, and returns safe response.
    """
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "")
    incoming_text = ""
    sender_number = "unknown"
    is_meta_webhook = False
    is_twilio = "application/x-www-form-urlencoded" in content_type or bool(request.headers.get("x-twilio-signature"))

    # Resolve dynamic environment configuration per request
    env = os.environ.get("ENVIRONMENT", ENVIRONMENT).lower()
    meta_secret = os.environ.get("META_APP_SECRET") or META_APP_SECRET
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN") or TWILIO_AUTH_TOKEN
    public_base_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") or PUBLIC_BASE_URL

    # 1. Handle Twilio Sandbox (application/x-www-form-urlencoded)
    if is_twilio:
        form_data = await request.form()
        twilio_sig = request.headers.get("x-twilio-signature")
        if env == "production" and not twilio_sig:
            raise HTTPException(status_code=401, detail="X-Twilio-Signature required in production")

        if twilio_token:
            if not twilio_sig:
                raise HTTPException(status_code=401, detail="X-Twilio-Signature required when TWILIO_AUTH_TOKEN is configured")

            if public_base_url:
                url = f"{public_base_url}{request.url.path}"
                if request.url.query:
                    url += f"?{request.url.query}"
            else:
                proto = request.headers.get("x-forwarded-proto", "")
                if proto.startswith("https"):
                    url = str(request.url).replace("http://", "https://", 1)
                else:
                    url = str(request.url)

            params = {k: str(v) for k, v in form_data.items()}
            if not verify_twilio_signature(url, params, twilio_sig):
                raise HTTPException(status_code=401, detail="Invalid Twilio signature")

        incoming_text = str(form_data.get("Body", "")).strip()
        sender_number = str(form_data.get("From", "unknown"))

    # 2. Handle Meta WhatsApp Cloud API or Direct JSON
    else:
        meta_sig = request.headers.get("x-hub-signature-256")

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        # Meta Cloud API payload format:
        # entry[0].changes[0].value.messages[0].text.body
        if "entry" in payload:
            is_meta_webhook = True
            if (env == "production" or meta_secret):
                if not meta_sig:
                    raise HTTPException(status_code=401, detail="X-Hub-Signature-256 required for Meta webhook")
                if not verify_meta_signature(raw_body, meta_sig):
                    raise HTTPException(status_code=401, detail="Invalid Meta signature")
            try:
                entry = payload.get("entry", [{}])[0]
                change = entry.get("changes", [{}])[0]
                value = change.get("value", {})
                messages = value.get("messages", [])
                if messages:
                    msg = messages[0]
                    # Outbound recipient must strictly come from the verified Meta message payload
                    sender_number = msg.get("from", "unknown")
                    if msg.get("type") == "text":
                        incoming_text = msg.get("text", {}).get("body", "")
            except Exception:
                pass
        else:
            # Direct JSON payload (e.g. {"message": "...", "from_number": "..."})
            # SECURITY ENFORCEMENT:
            # Direct unauthenticated JSON is ONLY permitted when ENVIRONMENT is development AND META_APP_SECRET is not configured.
            # In production, or whenever META_APP_SECRET is configured, unauthenticated requests are strictly rejected.
            if env == "production":
                raise HTTPException(
                    status_code=401,
                    detail="Direct unauthenticated JSON webhook is disabled in production. Meta or Twilio signed request required."
                )
            if meta_secret:
                raise HTTPException(
                    status_code=401,
                    detail="X-Hub-Signature-256 signature required when META_APP_SECRET is configured."
                )

            incoming_text = str(payload.get("message") or payload.get("Body") or payload.get("text") or "").strip()
            # Do NOT trust or use arbitrary user-supplied from_number for outbound messages
            sender_number = "dev_direct"

    if not incoming_text:
        return {"status": "ignored", "reason": "No readable text content found in webhook"}

    logger.info("Incoming WhatsApp from %s: '%s'", sender_number, incoming_text)

    # Execute Agentic Copilot
    bot_response = ask_agentic_copilot(incoming_text)
    answer_text = bot_response.get("content", "Maaf kijiye, abhi process nahi ho paya.")
    wa_formatted_text = format_for_whatsapp(answer_text)

    # Security rule: Outbound Meta API message is ONLY sent to senders verified from a genuine Meta Webhook payload
    access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN") or os.environ.get("WHATSAPP_TOKEN") or WHATSAPP_ACCESS_TOKEN
    phone_id = os.environ.get("WHATSAPP_PHONE_ID") or WHATSAPP_PHONE_ID
    if access_token and phone_id and is_meta_webhook and sender_number != "unknown" and sender_number != "dev_direct":
        try:
            url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            body = {
                "messaging_product": "whatsapp",
                "to": sender_number,
                "type": "text",
                "text": {"body": wa_formatted_text},
            }
            async with httpx.AsyncClient(timeout=6.0) as client:
                await client.post(url, headers=headers, json=body)
        except Exception as e:
            logger.warning("Outbound WhatsApp async dispatch error: %s", e)

    # Return response payload (supports XML-escaped Twilio TwiML format)
    if "application/x-www-form-urlencoded" in content_type:
        escaped_text = xml.sax.saxutils.escape(wa_formatted_text)
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{escaped_text}</Message>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    return {
        "status": "success",
        "sender": sender_number,
        "input_query": incoming_text,
        "bot_response": wa_formatted_text,
        "response": wa_formatted_text,
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
        "reply": format_for_whatsapp(response["content"]),
        "tool_called": response.get("tool_called"),
        "engine": response.get("engine"),
    }


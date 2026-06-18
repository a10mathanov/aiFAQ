"""YandexGPT service using HTTP REST and service account key (sa-key.json).

This implementation uses service account JWT auth to obtain an IAM token and
calls Yandex Cloud LLM completion REST API directly, bypassing unsupported gRPC
calls for the current environment.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import jwt
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

YANDEX_IAM_ENDPOINT = "iam.api.cloud.yandex.net"
YANDEX_LLM_ENDPOINT = "llm.api.cloud.yandex.net"
YANDEX_LLM_MODEL = "yandexgpt/latest"
YANDEX_LLM_URL = f"https://{YANDEX_LLM_ENDPOINT}/foundationModels/v1/completion"


class YandexGPTService:
    """REST client for Yandex Cloud LLM with service account auth."""

    def __init__(
        self,
        folder_id: str,
        sa_key_path: str = "sa-key.json",
        model: str = YANDEX_LLM_MODEL,
        api_url: Optional[str] = None,
        timeout: int = 30,
    ):
        self.folder_id = folder_id
        # Construct full model URI if only model name is provided
        if "://" not in model:
            self.model = f"gpt://{folder_id}/{model}"
        else:
            self.model = model
        self.api_url = api_url or YANDEX_LLM_URL
        self.timeout = timeout

        sa_path = Path(sa_key_path)
        if not sa_path.exists():
            raise FileNotFoundError(f"Service account key not found: {sa_key_path}")

        with sa_path.open("r", encoding="utf-8") as f:
            self.sa_key = json.load(f)

        self._validate_sa_key()
        self._iam_token: Optional[str] = None
        self._iam_token_expiry: Optional[datetime] = None

    def _validate_sa_key(self):
        required_keys = {"id", "service_account_id", "private_key"}
        missing = required_keys - set(self.sa_key.keys())
        if missing:
            raise ValueError(f"Invalid sa-key.json, missing keys: {missing}")

        private_key = self.sa_key.get("private_key")
        if not isinstance(private_key, str):
            raise ValueError("Invalid sa-key.json: 'private_key' must be a string.")

        private_key = private_key.strip()
        begin_marker = "-----BEGIN PRIVATE KEY-----"
        end_marker = "-----END PRIVATE KEY-----"
        if begin_marker not in private_key or end_marker not in private_key:
            raise ValueError(
                "Invalid sa-key.json: 'private_key' must contain a PEM private key block."
            )

        begin_index = private_key.index(begin_marker)
        end_index = private_key.rindex(end_marker) + len(end_marker)
        normalized_key = private_key[begin_index:end_index].strip()

        # Replace the key in memory with the normalized PEM block.
        self.sa_key["private_key"] = normalized_key

    def _get_jwt(self) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "iss": self.sa_key["service_account_id"],
            "aud": f"https://{YANDEX_IAM_ENDPOINT}/iam/v1/tokens",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=55)).timestamp()),
        }
        headers = {
            "typ": "JWT",
            "alg": "PS256",
            "kid": self.sa_key["id"],
        }
        private_key = self.sa_key["private_key"]
        return jwt.encode(payload, private_key, algorithm="PS256", headers=headers)

    async def _fetch_iam_token(self) -> str:
        jwt_token = self._get_jwt()
        url = f"https://{YANDEX_IAM_ENDPOINT}/iam/v1/tokens"
        data = {"jwt": jwt_token}

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=data) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"IAM token request failed {resp.status}: {text}")
                result = await resp.json()

        iam_token = result.get("iamToken")
        expires_at = result.get("expiresAt")
        if not iam_token or not expires_at:
            raise RuntimeError("IAM token response missing iamToken or expiresAt")

        self._iam_token = iam_token
        self._iam_token_expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        return iam_token

    async def _get_iam_token(self) -> str:
        if self._iam_token and self._iam_token_expiry:
            if datetime.now(timezone.utc) + timedelta(minutes=5) < self._iam_token_expiry:
                return self._iam_token

        return await self._fetch_iam_token()

    async def get_response(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        user_message: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Optional[str]:
        if messages is None:
            if not user_message or not user_message.strip():
                logger.warning("Empty message received")
                return None

            messages = []
            if system_prompt:
                messages.append({"role": "system", "text": system_prompt})
            messages.append({"role": "user", "text": user_message})
        else:
            if not isinstance(messages, list) or not messages:
                logger.warning("Empty messages list received")
                return None
            if system_prompt:
                messages.insert(
                    0, {"role": "system", "text": system_prompt}
                )

        try:
            iam_token = await self._get_iam_token()
        except Exception as exc:
            logger.error(f"Failed to get IAM token: {exc}")
            return None

        headers = {
            "Authorization": f"Bearer {iam_token}",
            "Content-Type": "application/json",
        }

        body: Dict[str, Any] = {
            "modelUri": self.model,
            "messages": messages,
            "temperature": 0.7,
            "maxTokens": 2000,
        }

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.api_url, json=body, headers=headers) as resp:
                    text = await resp.text()
                    if resp.status != 200:
                        logger.error(
                            "YandexGPT REST request failed %s: %s\nRequest URL: %s\nRequest body: %s",
                            resp.status,
                            text,
                            self.api_url,
                            body,
                        )
                        return None
                    result = await resp.json()
        except Exception as exc:
            logger.error(f"YandexGPT REST request exception: {exc}")
            return None

        # Extract answer from Yandex LLM completion response
        if isinstance(result, dict):
            # New format: result.alternatives[0].message.text
            if "result" in result and isinstance(result["result"], dict):
                alternatives = result["result"].get("alternatives", [])
                if alternatives and isinstance(alternatives, list):
                    first_alt = alternatives[0]
                    if isinstance(first_alt, dict) and "message" in first_alt:
                        message = first_alt["message"]
                        if isinstance(message, dict):
                            text = message.get("text")
                            if isinstance(text, str):
                                return text.strip()
            
            # Fallback: output field
            if "output" in result and isinstance(result["output"], str):
                return result["output"].strip()
            
            # Fallback: result.output field
            if "result" in result and isinstance(result["result"], dict):
                output = result["result"].get("output")
                if isinstance(output, str):
                    return output.strip()
            
            # Fallback: completion.text field
            if "completion" in result and isinstance(result["completion"], dict):
                text = result["completion"].get("text")
                if isinstance(text, str):
                    return text.strip()

        logger.error(f"Unexpected YandexGPT REST response structure: {result}")
        return None

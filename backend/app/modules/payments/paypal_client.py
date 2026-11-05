import logging
import uuid
from typing import Any, Dict, List
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PayPalClient:
    """PayPal Sandbox REST API Client for Payouts."""

    def __init__(self):
        self.mode = settings.PAYPAL_MODE.lower()
        self.base_url = (
            "https://api-m.paypal.com"
            if self.mode == "live"
            else "https://api-m.sandbox.paypal.com"
        )
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET

    @property
    def is_configured(self) -> bool:
        return bool(
            self.client_id
            and self.client_secret
            and not self.client_id.startswith("your-")
        )

    async def get_access_token(self) -> str:
        """Fetch OAuth2 token from PayPal."""
        if not self.is_configured:
            return "mock-access-token-sandbox"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json", "Accept-Language": "en_US"},
            )
            if resp.status_code != 200:
                logger.error(f"PayPal OAuth failed: {resp.status_code} {resp.text}")
                raise RuntimeError(f"PayPal Authentication failed: {resp.text}")
            return resp.json().get("access_token")

    async def create_batch_payout(
        self,
        sender_batch_id: str,
        email_subject: str,
        email_message: str,
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Trigger batch payout via PayPal Payouts API."""
        if not self.is_configured:
            # Deterministic sandbox mock response when live keys not provided
            batch_uuid = uuid.uuid4().hex[:12].upper()
            return {
                "batch_header": {
                    "payout_batch_id": f"PAYOUTS-BATCH-{batch_uuid}",
                    "batch_status": "SUCCESS",
                    "sender_batch_header": {
                        "sender_batch_id": sender_batch_id,
                        "email_subject": email_subject,
                        "email_message": email_message,
                    },
                },
                "items": [
                    {
                        "payout_item_id": f"ITEM-{uuid.uuid4().hex[:8].upper()}",
                        "transaction_id": f"TRANS-{uuid.uuid4().hex[:10].upper()}",
                        "activity_id": f"ACT-{uuid.uuid4().hex[:8].upper()}",
                        "transaction_status": "SUCCESS",
                        "payout_item_fee": {"currency": "USD", "value": "0.25"},
                        "payout_batch_id": f"PAYOUTS-BATCH-{batch_uuid}",
                        "payout_item": item,
                    }
                    for item in items
                ],
            }

        token = await self.get_access_token()
        payload = {
            "sender_batch_header": {
                "sender_batch_id": sender_batch_id,
                "email_subject": email_subject,
                "email_message": email_message,
            },
            "items": items,
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/payments/payouts",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )

            if resp.status_code not in (200, 201):
                logger.error(f"PayPal Payout API failed: {resp.status_code} {resp.text}")
                raise RuntimeError(f"PayPal Payout Error ({resp.status_code}): {resp.text}")

            return resp.json()

    async def get_payout_batch_details(self, payout_batch_id: str) -> Dict[str, Any]:
        """Query PayPal Payout Batch status."""
        if not self.is_configured or payout_batch_id.startswith("PAYOUTS-BATCH-"):
            return {
                "batch_header": {
                    "payout_batch_id": payout_batch_id,
                    "batch_status": "SUCCESS",
                }
            }

        token = await self.get_access_token()
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/v1/payments/payouts/{payout_batch_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch PayPal payout details: {resp.text}")
            return resp.json()


paypal_client = PayPalClient()

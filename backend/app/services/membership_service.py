"""
Membership Platform Integration Service

Handles integration with Skool membership platform for syncing user tiers and managing access.

Supports:
- Webhook processing for membership events
- User tier synchronization
- Platform-specific API communication
"""
import logging
import httpx
from typing import Optional, Dict, Any
from enum import Enum

from app.core.config import settings
from app.db.models import UserTier

logger = logging.getLogger(__name__)


class MembershipPlatform(str, Enum):
    """Supported membership platforms."""
    SKOOL = "skool"
    CUSTOM = "custom"


class MembershipEvent(str, Enum):
    """Membership event types from webhooks."""
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    PURCHASE_COMPLETED = "purchase.completed"


# Mapping of platform product IDs/names to our tiers
TIER_MAPPINGS: Dict[str, Dict[str, UserTier]] = {
    "skool": {
        "hair_hustlers_co": UserTier.BASIC,
        "hair_hustlers_co.": UserTier.BASIC,
        "hair_hustlers_elite": UserTier.VIP,
        "hair_hustlers_elite.": UserTier.VIP,
        "elite": UserTier.VIP,
        "basic": UserTier.BASIC,
        "community": UserTier.BASIC,
    },
    "custom": {
        "basic": UserTier.BASIC,
        "trial": UserTier.BASIC,
        "elite": UserTier.VIP,
        "vip": UserTier.VIP,
    }
}


class MembershipService:
    """
    Service for membership platform integration.
    
    Handles webhook processing and user synchronization
    with external membership platforms.
    """
    
    def __init__(self, platform: MembershipPlatform = MembershipPlatform.CUSTOM):
        self.platform = platform
        self.api_url = settings.MEMBERSHIP_PLATFORM_API_URL
        # Use Skool-specific secret if available, otherwise use generic API key
        if platform == MembershipPlatform.SKOOL and settings.SKOOL_WEBHOOK_SECRET:
            self.api_key = settings.SKOOL_WEBHOOK_SECRET
        else:
            self.api_key = settings.MEMBERSHIP_PLATFORM_API_KEY
        self.tier_mapping = TIER_MAPPINGS.get(platform.value, TIER_MAPPINGS["custom"])
    
    # =========================================================================
    # Webhook Processing
    # =========================================================================
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature from membership platform.
        
        Args:
            payload: Raw request body
            signature: Signature header from request
            
        Returns:
            True if signature is valid
        """
        import hmac
        import hashlib
        
        if not self.api_key:
            logger.warning("No API key configured for webhook verification")
            return True  # Allow in development
        
        expected = hmac.new(
            self.api_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    def parse_webhook_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse webhook payload into standardized format.
        
        Args:
            data: Raw webhook data
            
        Returns:
            Standardized event data with:
            - event_type: MembershipEvent
            - user_email: User's email
            - user_name: User's name
            - product_id: Product/tier identifier
            - metadata: Additional data
        """
        if self.platform == MembershipPlatform.SKOOL:
            return self._parse_skool_webhook(data)
        else:
            return self._parse_custom_webhook(data)
    
    def _parse_skool_webhook(self, data: Dict) -> Dict[str, Any]:
        """
        Parse Skool webhook format.
        
        Skool webhooks can come in different formats:
        1. Direct webhook from Skool plugin
        2. Via Zapier (most common)
        3. Custom format
        
        Expected formats:
        - Direct: {"event": "member.joined", "member": {...}, "group": {...}}
        - Zapier: {"event": "...", "data": {...}}
        """
        # Handle Zapier format (most common for Skool)
        if "data" in data:
            zapier_data = data.get("data", {})
            member = zapier_data.get("member", {}) or zapier_data.get("user", {})
            group = zapier_data.get("group", {}) or zapier_data.get("community", {})
            
            event_type = data.get("event", "")
            event_mapping = {
                "member.joined": MembershipEvent.USER_CREATED,
                "member.paid": MembershipEvent.SUBSCRIPTION_CREATED,
                "member.updated": MembershipEvent.USER_UPDATED,
                "member.cancelled": MembershipEvent.SUBSCRIPTION_CANCELLED,
                "payment.completed": MembershipEvent.PURCHASE_COMPLETED,
            }
            
            # Determine tier from group name
            group_name = group.get("name", "").lower().replace(" ", "_").replace(".", "")
            product_id = group_name
            
            return {
                "event_type": event_mapping.get(event_type, event_type),
                "user_email": member.get("email") or zapier_data.get("email"),
                "user_name": member.get("name") or member.get("username") or zapier_data.get("name"),
                "product_id": product_id,
                "metadata": {
                    "skool_member_id": member.get("id"),
                    "skool_group_id": group.get("id"),
                    "skool_group_name": group.get("name"),
                    "source": "zapier" if "data" in data else "skool",
                }
            }
        
        # Handle direct Skool webhook format
        member = data.get("member", {}) or data.get("user", {})
        group = data.get("group", {}) or data.get("community", {})
        
        event_type = data.get("event", data.get("event_type", ""))
        event_mapping = {
            "member.joined": MembershipEvent.USER_CREATED,
            "member.paid": MembershipEvent.SUBSCRIPTION_CREATED,
            "member.updated": MembershipEvent.USER_UPDATED,
            "member.cancelled": MembershipEvent.SUBSCRIPTION_CANCELLED,
            "payment.completed": MembershipEvent.PURCHASE_COMPLETED,
        }
        
        # Determine tier from group name
        group_name = group.get("name", "").lower().replace(" ", "_").replace(".", "")
        product_id = group_name or data.get("tier", "basic")
        
        return {
            "event_type": event_mapping.get(event_type, event_type),
            "user_email": member.get("email") or data.get("email"),
            "user_name": member.get("name") or member.get("username") or data.get("name"),
            "product_id": product_id,
            "metadata": {
                "skool_member_id": member.get("id"),
                "skool_group_id": group.get("id"),
                "skool_group_name": group.get("name"),
                "source": "skool",
            }
        }
    
    def _parse_custom_webhook(self, data: Dict) -> Dict[str, Any]:
        """Parse custom/generic webhook format."""
        return {
            "event_type": data.get("event_type", data.get("event")),
            "user_email": data.get("email", data.get("user_email")),
            "user_name": data.get("name", data.get("user_name")),
            "product_id": data.get("tier", data.get("product_id", "basic")),
            "metadata": data.get("metadata", {})
        }
    
    # =========================================================================
    # Tier Resolution
    # =========================================================================
    
    def resolve_tier(self, product_id: str) -> UserTier:
        """
        Resolve product ID to user tier.
        
        Args:
            product_id: Product identifier from platform
            
        Returns:
            Corresponding UserTier
        """
        product_lower = product_id.lower()
        
        # Try exact match first
        if product_lower in self.tier_mapping:
            return self.tier_mapping[product_lower]
        
        # Try partial match
        for key, tier in self.tier_mapping.items():
            if key in product_lower or product_lower in key:
                return tier
        
        # Check for tier keywords
        if "vip" in product_lower or "elite" in product_lower:
            return UserTier.VIP
        
        # Skool-specific: Hair Hu$tlers Co = Basic, Hair Hu$tlers ELITE = VIP
        if "hair_hustlers" in product_lower:
            if "elite" in product_lower:
                return UserTier.VIP
            return UserTier.BASIC
        
        # Default to basic (trial)
        return UserTier.BASIC
    
    # =========================================================================
    # Platform API Communication
    # =========================================================================
    
    async def fetch_user_from_platform(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user data from membership platform API.
        
        Args:
            email: User's email address
            
        Returns:
            User data from platform or None if not found
        """
        if not self.api_url or not self.api_key:
            logger.warning("Membership platform API not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/users",
                    params={"email": email},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    logger.error(f"Platform API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to fetch user from platform: {e}")
            return None
    
    async def sync_user_tier(self, email: str) -> Optional[UserTier]:
        """
        Sync user tier from membership platform.
        
        Args:
            email: User's email address
            
        Returns:
            User's tier from platform or None if not found
        """
        user_data = await self.fetch_user_from_platform(email)
        if not user_data:
            return None
        
        # Extract product/subscription info
        subscriptions = user_data.get("subscriptions", [])
        if subscriptions:
            # Get highest tier from active subscriptions
            tiers = [
                self.resolve_tier(sub.get("product_id", ""))
                for sub in subscriptions
                if sub.get("status") == "active"
            ]
            if tiers:
                # Return highest tier (VIP > BASIC)
                tier_order = {UserTier.VIP: 2, UserTier.BASIC: 1}
                return max(tiers, key=lambda t: tier_order.get(t, 0))
        
        return UserTier.BASIC

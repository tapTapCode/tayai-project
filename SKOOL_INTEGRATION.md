# Skool Integration Guide

This guide explains how to integrate Skool (Hair Hu$tlers Co) with TayAI for automatic membership synchronization.

## Overview

Skool integration allows TayAI to:
- Automatically create/update users when they join Skool communities
- Sync membership tiers (Hair Hu$tlers Co = Basic, Hair Hu$tlers ELITE = VIP)
- Handle membership cancellations and upgrades
- Keep user access in sync with Skool membership status

## Skool Community Structure

Based on [Hair Hu$tlers Co](https://www.skool.com/tla-hair-hutlers-co/about):

- **Hair Hu$tlers Co** ($37/month) → Maps to **Basic** tier in TayAI
- **Hair Hu$tlers ELITE** (upgrade option) → Maps to **VIP/Elite** tier in TayAI

## Integration Methods

Skool doesn't have a direct REST API, but supports integration through:

1. **Webhooks** (via Skool Plugins) - Recommended
2. **Zapier** (as middleware) - Most flexible
3. **Manual Sync** (via member exports)

---

## Method 1: Direct Skool Webhooks (If Available)

### Setup Steps

1. **Enable Webhook Plugin in Skool:**
   - Go to your Skool group settings
   - Navigate to "Plugins" section
   - Find "Webhook" plugin and toggle it ON
   - Click "Edit" to configure

2. **Configure Webhook URL:**
   ```
   https://your-domain.com/api/v1/membership/webhook/skool
   ```

3. **Set Webhook Secret:**
   - Generate a secure secret key
   - Add to your `.env` file:
   ```bash
   MEMBERSHIP_PLATFORM_API_KEY=your_skool_webhook_secret
   ```

4. **Test Webhook:**
   - Skool will send test events when a member joins
   - Check your backend logs to verify events are received

### Webhook Events Handled

- `member.joined` → Creates user with Basic tier
- `member.paid` → Confirms subscription, updates tier
- `member.updated` → Updates user information
- `member.cancelled` → Downgrades to Basic or deactivates

---

## Method 2: Zapier Integration (Recommended)

Since Skool has robust Zapier support, this is the most reliable method.

### Setup Steps

#### Step 1: Get Skool API Key

1. In Skool, go to **Plugins** section
2. Enable **Zapier** integration
3. Copy your **API Key**

#### Step 2: Create Zap in Zapier

1. **Trigger:** Skool
   - Event: "New Paid Member" or "Member Joined"
   - Connect your Skool account using the API key

2. **Action:** Webhooks by Zapier
   - Event: "POST"
   - URL: `https://your-domain.com/api/v1/membership/webhook/skool`
   - Method: POST
   - Headers:
     ```json
     {
       "Content-Type": "application/json",
       "X-Platform": "skool"
     }
     ```
   - Data (JSON):
     ```json
     {
       "event": "member.joined",
       "data": {
         "member": {
           "email": "{{member_email}}",
           "name": "{{member_name}}",
           "id": "{{member_id}}"
         },
         "group": {
           "name": "{{group_name}}",
           "id": "{{group_id}}"
         }
       }
     }
     ```

#### Step 3: Map Skool Groups to TayAI Tiers

In Zapier, use filters or formatters to map:
- **Hair Hu$tlers Co** → `"hair_hustlers_co"`
- **Hair Hu$tlers ELITE** → `"hair_hustlers_elite"`

#### Step 4: Test and Activate

1. Test the Zap with a sample member
2. Verify webhook is received in TayAI backend
3. Activate the Zap

### Additional Zaps to Create

1. **Member Cancelled:**
   - Trigger: Skool "Member Cancelled"
   - Action: Webhook to TayAI with `event: "member.cancelled"`

2. **Member Upgraded:**
   - Trigger: Skool "Member Joined" (filter by group = ELITE)
   - Action: Webhook to TayAI with tier = VIP

---

## Method 3: Manual Sync (Fallback)

If webhooks aren't available, you can manually sync members:

### Using Skool Member Export

1. Export member list from Skool (CSV)
2. Use the sync endpoint:

```bash
POST /api/v1/membership/sync
{
  "email": "member@example.com",
  "platform": "skool"
}
```

Or use the admin endpoint to create members:

```bash
POST /api/v1/membership/members
{
  "email": "member@example.com",
  "tier": "basic",  // or "vip" for ELITE
  "is_active": true
}
```

---

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Skool Integration
MEMBERSHIP_PLATFORM_API_URL=https://api.skool.com  # If Skool adds API
MEMBERSHIP_PLATFORM_API_KEY=your_webhook_secret_key

# Upgrade URLs (for Skool)
UPGRADE_URL_BASIC=https://www.skool.com/tla-hair-hutlers-co/about
UPGRADE_URL_VIP=https://www.skool.com/tla-hair-hutlers-elite/about  # Update with actual ELITE URL
UPGRADE_URL_GENERIC=https://www.skool.com/tla-hair-hutlers-co/about
```

### Tier Mappings

The system automatically maps:
- `hair_hustlers_co` → Basic tier
- `hair_hustlers_elite` → VIP/Elite tier
- Any group with "elite" in name → VIP tier
- Default → Basic tier

---

## Testing the Integration

### Test Webhook Manually

```bash
curl -X POST https://your-domain.com/api/v1/membership/webhook/skool \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: your_secret" \
  -d '{
    "event": "member.joined",
    "data": {
      "member": {
        "email": "test@example.com",
        "name": "Test User",
        "id": "123"
      },
      "group": {
        "name": "Hair Hu$tlers Co.",
        "id": "group_123"
      }
    }
  }'
```

### Expected Response

```json
{
  "status": "created",
  "email": "test@example.com",
  "tier": "basic"
}
```

---

## Webhook Payload Formats

### Direct Skool Webhook Format

```json
{
  "event": "member.joined",
  "member": {
    "email": "user@example.com",
    "name": "John Doe",
    "id": "member_123"
  },
  "group": {
    "name": "Hair Hu$tlers Co.",
    "id": "group_123"
  }
}
```

### Zapier Format (Recommended)

```json
{
  "event": "member.joined",
  "data": {
    "member": {
      "email": "user@example.com",
      "name": "John Doe",
      "id": "member_123"
    },
    "group": {
      "name": "Hair Hu$tlers Co.",
      "id": "group_123"
    }
  }
}
```

---

## Troubleshooting

### Webhook Not Receiving Events

1. **Check Skool Plugin Settings:**
   - Ensure webhook plugin is enabled
   - Verify webhook URL is correct
   - Check for any error messages in Skool

2. **Check Zapier (if using):**
   - Verify Zap is active
   - Check Zap history for errors
   - Test the webhook step manually

3. **Check Backend Logs:**
   ```bash
   # View webhook logs
   docker-compose logs backend | grep webhook
   ```

4. **Verify Webhook Endpoint:**
   ```bash
   # Test endpoint is accessible
   curl https://your-domain.com/api/v1/membership/webhook/skool
   ```

### Users Not Created/Updated

1. **Check Email Format:**
   - Ensure email is provided in webhook payload
   - Verify email format is valid

2. **Check Tier Mapping:**
   - Review group name in webhook payload
   - Verify it matches tier mapping rules

3. **Check Database:**
   - Verify user table has proper permissions
   - Check for any constraint violations

### Signature Verification Failing

1. **Verify Secret Key:**
   - Ensure `MEMBERSHIP_PLATFORM_API_KEY` matches Skool/Zapier secret
   - Check for whitespace or encoding issues

2. **Check Header Name:**
   - Skool may use different header name
   - Update `verify_webhook_signature()` if needed

---

## Security Considerations

1. **Webhook Secret:**
   - Use a strong, random secret key
   - Store securely in environment variables
   - Never commit to version control

2. **HTTPS Required:**
   - Always use HTTPS for webhook URLs
   - Skool/Zapier require HTTPS endpoints

3. **Rate Limiting:**
   - Skool webhooks are rate-limited
   - Implement retry logic for failed webhooks

4. **Idempotency:**
   - Webhook handler is idempotent
   - Duplicate events won't create duplicate users

---

## Next Steps

1. **Set up webhook endpoint** (Method 1 or 2)
2. **Test with a sample member**
3. **Monitor webhook logs** for first few days
4. **Set up alerts** for webhook failures
5. **Document any custom mappings** needed

---

## Support

For Skool-specific issues:
- [Skool Help Center](https://help.skool.com)
- [Skool Zapier Integration](https://help.skool.com/article/56-zapier-integration)

For TayAI integration issues:
- Check backend logs
- Review webhook endpoint responses
- Verify tier mappings in code

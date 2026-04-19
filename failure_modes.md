# ⚠️ Failure Modes

## 1. Missing Order ID

If order_id is missing, the system sends a reply asking for more details.

## 2. Order Not Found

If the order is not found, the system escalates the issue.

## 3. Refund Not Eligible

If refund is not allowed, the system informs the user via send_reply.

## 4. No Tool Triggered

Fallback logic ensures a reply is always sent.

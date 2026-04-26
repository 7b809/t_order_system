🚀 🔥 DHAN TRADING API DOCS (YOUR SYSTEM)
🌐 BASE URL
http://127.0.0.1:5000
🧪 MODE HANDLING
Mode	How it works
LIVE	TESTING_FLAG=false
TEST (AMO)	TESTING_FLAG=true

👉 Controlled via .env

TESTING_FLAG=true   # AMO mode
📌 1. PLACE ORDER API
🔹 Endpoint
POST /order
🔹 Request Body (FULL FORMAT)
{
  "security_id": "72317",
  "exchange_segment": "NSE_FNO",
  "transaction_type": "BUY",
  "quantity": 50,
  "product_type": "INTRADAY",
  "price": 0,
  "market": true
}
🔹 Fields Explained
Field	Type	Required	Description
security_id	string	✅	Instrument ID
exchange_segment	string	❌	NSE_EQ / NSE_FNO
transaction_type	string	❌	BUY / SELL
quantity	int	❌	Lot size
product_type	string	❌	INTRADAY / DELIVERY
price	float	❌	Required for LIMIT
market	bool	❌	true = MARKET
🔹 Behavior
✅ LIVE MODE
TESTING_FLAG = false
→ Normal order placed
🧪 TEST MODE (AMO)
TESTING_FLAG = true
→ after_market_order = true
→ Order queued (not executed immediately)
🔹 Response
{
  "status": "success",
  "data": {
    "status": "success",
    "data": {
      "orderId": "2352604267107",
      "orderStatus": "TRANSIT"
    }
  }
}
🔹 Order Status Meaning
Status	Meaning
TRANSIT	Order accepted
OPEN	Sent to exchange
TRADED	Executed
CANCELLED	Cancelled
REJECTED	Failed
❌ 2. CANCEL ORDER API
🔹 Endpoint
POST /cancel
🔹 Request
{
  "order_id": "2352604267107"
}
🔹 Response
{
  "status": "success",
  "data": {
    "data": {
      "orderId": "2352604267107",
      "orderStatus": "CANCELLED"
    }
  }
}
⚠️ Rules
Condition	Result
TRANSIT / OPEN	✅ Can cancel
TRADED	❌ Cannot cancel
🔄 3. EXIT POSITION API
🔹 Endpoint
POST /exit
🔹 Request
{
  "security_id": "72317",
  "exchange_segment": "NSE_FNO",
  "quantity": 50,
  "product_type": "INTRADAY"
}
🔹 Behavior
Always places opposite SELL order (current logic)

⚠️ Note:

Currently not smart (does not detect BUY/SELL automatically)
🔹 Response

Same as place order

❤️ 4. HEALTH CHECK
GET /health
Response
{
  "status": "ok"
}
📊 5. DASHBOARD
GET /

👉 Returns HTML UI (Bootstrap dashboard)

🔥 MODE COMPARISON
Feature	LIVE	TEST (AMO)
Execution	Immediate	Next session
Risk	High	Safe
Use case	Real trading	Testing
Flag	false	true
⚠️ IMPORTANT RULES
❗ 1. F&O Quantity

Must match lot size:

NIFTY → 50
BANKNIFTY → 15
❗ 2. AMO Behavior
Order → TRANSIT → executes next day
❗ 3. LIMIT vs MARKET
MARKET → immediate execution
LIMIT → controlled price
🚀 SAMPLE CURL
🔹 Place Order
curl -X POST http://127.0.0.1:5000/order \
-H "Content-Type: application/json" \
-d "{\"security_id\":\"72317\",\"quantity\":50}"
🔹 Cancel
curl -X POST http://127.0.0.1:5000/cancel \
-H "Content-Type: application/json" \
-d "{\"order_id\":\"2352604267107\"}"
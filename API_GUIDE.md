# Restaurant Order Management API - Guide

## API Endpoints

### 📋 Orders

#### List All Orders
```http
GET /api/orders/
```

**Query Parameters:**
- `restaurant_id` - Filter by restaurant ID
- `status` - Filter by order status (created, accepted, preparing, ready, delivered, cancelled)
- `preparation_status` - Filter by preparation status (pending, accepted, rejected, delayed, cancelled, done)

**Example:**
```bash
# Get all orders for Pizza Paradise (ID: 1)
curl /api/orders/?restaurant_id=1
```

#### Get Pending Orders
```http
GET /api/orders/pending/
```
Returns orders waiting for restaurant response (created but not accepted/rejected)

**Example:**
```bash
curl /api/orders/pending/?restaurant_id=1
```

#### Get Active Orders
```http
GET /api/orders/active/
```
Returns orders currently being prepared (accepted or delayed)

**Example:**
```bash
curl /api/orders/active/?restaurant_id=1
```

#### Get Order Details
```http
GET /api/orders/{id}/
```

**Example:**
```bash
curl /api/orders/1/
```

---

### 🎯 Order Actions

#### Accept Order Preparation
```http
POST /api/orders/{id}/accept_preparation/
```

**Request Body:** None required

**Example:**
```bash
curl -X POST /api/orders/1/accept_preparation/
```

**Response:**
```json
{
  "id": 1,
  "status": "created",
  "preparation_status": "accepted",
  "accepted_at": "2025-10-20T12:30:00Z",
  ...
}
```

**Mock Backend Notification:**
```
🚀 KYTE BACKEND NOTIFICATION
Event Type: PREPARATION_ACCEPTED
Order ID: 1
```

---

### 🔔 Kyte Webhook (Inbound)

Mock endpoint to receive events from Kyte.

#### Receive Event
```http
POST /api/kyte/events/
```

**Body:**
```json
{
  "type": "order_created",
  "data": {
    "restaurant_id": 1,
    "customer_id": 1,
    "total_amount": 25.50,
    "placed_at": "2025-10-20T12:00:00Z",
    "items": [
      {"menu_item": "Margherita", "quantity": 1, "unit_price": 12.5}
    ]
  }
}
```

Supported `type` values:
- `order_created`: creates a local order (status `created`, preparation `pending`).
- `order_cancelled`: cancels an existing order.

Examples:
```bash
curl -X POST /api/kyte/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "order_cancelled",
    "data": {"order_id": 1, "reason": "Customer request"}
  }'
```

---

#### Reject Order Preparation
```http
POST /api/orders/{id}/reject_preparation/
```

**Request Body:**
```json
{
  "reason": "We are out of ingredients"
}
```

**Example:**
```bash
curl -X POST /api/orders/1/reject_preparation/ \
  -H "Content-Type: application/json" \
  -d '{"reason": "Kitchen is at capacity"}'
```

**Response:**
```json
{
  "id": 1,
  "status": "cancelled",
  "preparation_status": "rejected",
  "rejection_reason": "Kitchen is at capacity",
  "cancelled_at": "2025-10-20T12:35:00Z",
  ...
}
```

**Mock Backend Notification:**
```
🚀 KYTE BACKEND NOTIFICATION
Event Type: PREPARATION_REJECTED
Order ID: 1
Data: {"reason": "Kitchen is at capacity"}
```

---

#### Mark Order as Delayed
```http
POST /api/orders/{id}/mark_delayed/
```

**Request Body:**
```json
{
  "delay_minutes": 15,
  "reason": "High order volume" // optional
}
```

**Example:**
```bash
curl -X POST /api/orders/1/mark_delayed/ \
  -H "Content-Type: application/json" \
  -d '{"delay_minutes": 20, "reason": "Waiting for delivery driver"}'
```

**Response:**
```json
{
  "id": 1,
  "preparation_status": "delayed",
  "delay_minutes": 20,
  ...
}
```

**Mock Backend Notification:**
```
🚀 KYTE BACKEND NOTIFICATION
Event Type: PREPARATION_DELAYED
Order ID: 1
Data: {"delay_minutes": 20, "reason": "Waiting for delivery driver"}
```

---

#### Cancel Order Preparation
```http
POST /api/orders/{id}/mark_cancelled/
```

**Request Body:**
```json
{
  "reason": "Customer requested cancellation"
}
```

**Example:**
```bash
curl -X POST /api/orders/1/mark_cancelled/ \
  -H "Content-Type: application/json" \
  -d '{"reason": "Equipment malfunction"}'
```

**Response:**
```json
{
  "id": 1,
  "status": "cancelled",
  "preparation_status": "cancelled",
  "rejection_reason": "Equipment malfunction",
  "cancelled_at": "2025-10-20T13:00:00Z",
  ...
}
```

---

#### Mark Order as Done
```http
POST /api/orders/{id}/mark_done/
```

**Request Body:** None required

**Example:**
```bash
curl -X POST /api/orders/1/mark_done/
```

**Response:**
```json
{
  "id": 1,
  "status": "ready",
  "preparation_status": "done",
  ...
}
```

**Mock Backend Notification:**
```
🚀 KYTE BACKEND NOTIFICATION
Event Type: PREPARATION_DONE
Order ID: 1
```

In this mock integration, outbound notifications are logged server-side. When any of the actions above are invoked, the app logs a line similar to:

```
KYTE OUTBOUND → preparation_accepted | payload={'order_id': 1}
```

---

### 🏢 Restaurants

#### List Restaurants
```http
GET /api/restaurants/
```

#### Get Restaurant Details
```http
GET /api/restaurants/{id}/
```

---

### 👥 Customers

#### List Customers
```http
GET /api/customers/
```

#### Get Customer Details
```http
GET /api/customers/{id}/
```

---

### 📦 Order Items

#### List Order Items
```http
GET /api/order-items/
```

---

### 📜 Order Events (Audit Log)

#### List Order Events
```http
GET /api/order-events/
```

**Query Parameters:**
- `order_id` - Filter events by order ID

**Example:**
```bash
curl /api/order-events/?order_id=1
```

---

## Order Status Flow

### Order Status
- `created` → `accepted` → `preparing` → `ready` → `delivered`
- Can be cancelled at any point → `cancelled`

### Preparation Status
- `null/pending` → Restaurant receives order
- `accepted` → Restaurant accepts preparation
- `rejected` → Restaurant rejects (order cancelled)
- `delayed` → Restaurant needs more time
- `cancelled` → Restaurant cancels after accepting
- `done` → Order preparation complete


## Database Models

### Customer
- `first_name`, `second_name`, `phone_number`, `address`

### Restaurant
- `name`, `address`, `phone_number`

### Order
- `restaurant` (FK), `customer` (FK)
- `status`, `preparation_status`
- `total_amount`, `rejection_reason`, `delay_minutes`
- `placed_at`, `accepted_at`, `delivered_at`, `cancelled_at`

### OrderItem
- `order` (FK)
- `menu_item`, `quantity`, `unit_price`

### OrderEvent
- `order` (FK)
- `event_type`, `event_data`, `created_at`

---


## Development Notes

- All timestamps use UTC timezone
- IDs are auto-incremented BigIntegers
- Order events are created automatically for audit trail
- Preparation status transitions are validated

---
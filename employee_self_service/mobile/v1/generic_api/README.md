# Generic CRUD APIs

Simple generic APIs that work with any Frappe DocType without custom code.

## Overview

This module provides 4 generic APIs:
1. **get_list** - Get paginated list with optional aggregations
2. **get_details** - Get complete document details
3. **create** - Create new or update existing document
4. **update** - Update existing document by name

---

## APIs

### 1. Get List

Get paginated list of documents with optional child table aggregations.

**Endpoint:**
```
POST /api/method/employee_self_service.mobile.v1.generic_api.api.get_list
```

**Parameters:**
- `doctype` (required) - DocType name
- `fields` (optional) - List of field names (defaults to list view fields from meta)
- `filters` (optional) - Filter list/dict
- `start` (optional) - Pagination start (default: 0)
- `page_length` (optional) - Records per page (default: 20)
- `order_by` (optional) - Sort order (default: "modified desc")
- `aggregate` (optional) - List of aggregation configs for child tables

**Aggregation Format:**
```json
[
  {
    "table_name": "Purchase Order Item",
    "function": "count",
    "field_name": ""
  },
  {
    "table_name": "Purchase Order Item",
    "function": "sum",
    "field_name": "qty"
  }
]
```

**Examples:**

Simple list:
```bash
POST /api/method/employee_self_service.mobile.v1.generic_api.api.get_list
Body: {
  "doctype": "Purchase Order"
}
```

With filters:
```bash
POST /api/method/employee_self_service.mobile.v1.generic_api.api.get_list
Body: {
  "doctype": "Purchase Order",
  "filters": [["status", "=", "Draft"]]
}
```

With aggregations:
```bash
POST /api/method/employee_self_service.mobile.v1.generic_api.api.get_list
Body: {
  "doctype": "Purchase Order",
  "aggregate": [
    {"table_name": "Purchase Order Item", "function": "count", "field_name": ""},
    {"table_name": "Purchase Order Item", "function": "sum", "field_name": "qty"}
  ]
}
```

**Response:**
```json
{
  "http_status_code": 200,
  "message": "List Details Get Successfully",
  "data": [
    {
      "name": "PO-001",
      "supplier": "SUP-001",
      "status": "Draft",
      "items_count": 5,
      "total_qty": 100
    }
  ]
}
```

---

### 2. Get Details

Get complete document with all fields including child tables.

**Endpoint:**
```
POST /api/method/employee_self_service.mobile.v1.generic_api.api.get_details
```

**Parameters:**
- `doctype` (required) - DocType name
- `name` (required) - Document name/ID

**Example:**
```bash
POST /api/method/employee_self_service.mobile.v1.generic_api.api.get_details
Body: {
  "doctype": "Purchase Order",
  "name": "PO-001"
}
```

**Response:**
```json
{
  "http_status_code": 200,
  "message": "Document Details Get Successfully",
  "data": {
    "name": "PO-001",
    "supplier": "SUP-001",
    "status": "Draft",
    "items": [
      {
        "item_code": "ITEM-001",
        "qty": 10,
        "rate": 100
      }
    ],
    "...": "all other fields"
  }
}
```

---

### 3. Create

Create a new document or update existing one (if name is provided).

**Endpoint:**
```
POST /api/method/employee_self_service.mobile.v1.generic_api.api.create
```

**Parameters:**
- `doctype` (required) - DocType name
- `name` (optional) - Document name (if provided, updates existing doc)
- `save_action` (optional) - "save" or "submit" (default: "save")
- All other fields - Document field values including child tables

**Example - Create New:**
```bash
POST /api/method/employee_self_service.mobile.v1.generic_api.api.create
Body: {
  "doctype": "Purchase Order",
  "supplier": "SUP-001",
  "schedule_date": "2025-12-01",
  "items": [
    {
      "item_code": "ITEM-001",
      "qty": 10,
      "rate": 100
    }
  ],
  "save_action": "save"
}
```

**Example - Update Existing:**
```bash
POST /api/method/employee_self_service.mobile.v1.generic_api.api.create
Body: {
  "doctype": "Purchase Order",
  "name": "PO-001",
  "supplier": "SUP-002",
  "save_action": "submit"
}
```

**Response:**
```json
{
  "http_status_code": 200,
  "message": "Purchase Order has been saved successfully",
  "data": {
    "name": "PO-001",
    "docstatus": 0
  }
}
```

---

### 4. Update

Update an existing document (draft documents only).

**Endpoint:**
```
POST /api/method/employee_self_service.mobile.v1.generic_api.api.update
```

**Parameters:**
- `doctype` (required) - DocType name
- `name` (required) - Document name/ID
- `save_action` (optional) - "save" or "submit" (default: "save")
- All other fields - Document field values to update

**Example:**
```bash
POST /api/method/employee_self_service.mobile.v1.generic_api.api.update
Body: {
  "doctype": "Purchase Order",
  "name": "PO-001",
  "status": "Approved",
  "remarks": "Approved by manager",
  "save_action": "submit"
}
```

**Response:**
```json
{
  "http_status_code": 200,
  "message": "Purchase Order has been submitted successfully",
  "data": {
    "name": "PO-001",
    "docstatus": 1
  }
}
```

**Note:** Cannot update submitted (docstatus=1) or cancelled (docstatus=2) documents.

---

## Features

**Works with any DocType** - Purchase Order, Sales Order, Leave Application, etc.  
**Auto-discovers list fields** - From DocType meta if not specified  
**Child table aggregations** - Count items or sum fields (count, sum)  
**Complete document returns** - All fields including child tables  
**Save and submit actions** - Control document workflow  
**Proper error logging** - With title and message parameters  
**Pagination support** - For large datasets  
**Flexible filtering** - Multiple filter options  

---

## Aggregation Functions

The `aggregate` parameter supports:

### Count Function
Counts the number of child table records.

```json
{"table_name": "Purchase Order Item", "function": "count", "field_name": ""}
```
Returns: `items_count` field in each document

### Sum Function
Sums a specific field in child table records.

```json
{"table_name": "Purchase Order Item", "function": "sum", "field_name": "qty"}
```
Returns: `total_qty` field in each document

### Multiple Aggregations
You can combine multiple aggregations:

```json
{
  "doctype": "Sales Order",
  "aggregate": [
    {"table_name": "Sales Order Item", "function": "count", "field_name": ""},
    {"table_name": "Sales Order Item", "function": "sum", "field_name": "qty"},
    {"table_name": "Sales Order Item", "function": "sum", "field_name": "amount"}
  ]
}
```

Returns each document with:
- `items_count` - Number of items
- `total_qty` - Total quantity
- `total_amount` - Total amount

---

## Usage Examples

### JavaScript/React Native

```javascript
// Get list with aggregations
const getOrders = async () => {
  const response = await fetch(
    `/api/method/employee_self_service.mobile.v1.generic_api.api.get_list`,
    {
      method: 'POST',
      headers: {
        'Authorization': `token ${apiKey}:${apiSecret}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        doctype: 'Purchase Order',
        filters: [['status', '=', 'Draft']],
        aggregate: [
          {table_name: 'Purchase Order Item', function: 'count', field_name: ''},
          {table_name: 'Purchase Order Item', function: 'sum', field_name: 'qty'}
        ]
      })
    }
  );
  const data = await response.json();
  return data.data;
};

// Get document details
const getOrderDetails = async (orderId) => {
  const response = await fetch(
    `/api/method/employee_self_service.mobile.v1.generic_api.api.get_details`,
    {
      method: 'POST',
      headers: {
        'Authorization': `token ${apiKey}:${apiSecret}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        doctype: 'Purchase Order',
        name: orderId
      })
    }
  );
  const data = await response.json();
  return data.data;
};

// Create new order
const createOrder = async (orderData) => {
  const response = await fetch(
    `/api/method/employee_self_service.mobile.v1.generic_api.api.create`,
    {
      method: 'POST',
      headers: {
        'Authorization': `token ${apiKey}:${apiSecret}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        doctype: 'Purchase Order',
        ...orderData,
        save_action: 'save'
      })
    }
  );
  const data = await response.json();
  return data.data;
};

// Update order
const updateOrder = async (orderId, updates) => {
  const response = await fetch(
    `/api/method/employee_self_service.mobile.v1.generic_api.api.update`,
    {
      method: 'POST',
      headers: {
        'Authorization': `token ${apiKey}:${apiSecret}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        doctype: 'Purchase Order',
        name: orderId,
        ...updates,
        save_action: 'submit'
      })
    }
  );
  const data = await response.json();
  return data.data;
};
```

---

## Error Handling

All errors are logged with proper title and message:

```python
frappe.log_error(
    title=f"Generic API - {operation} error for {doctype}",
    message=frappe.get_traceback()
)
```

Aggregation errors don't fail the entire request - they're logged and the list is returned without aggregation data.

---

## Response Format

All APIs use the standard `gen_response` format:

```json
{
  "http_status_code": 200,
  "message": "Success message",
  "data": { ... }
}
```

Error responses:

```json
{
  "http_status_code": 500,
  "message": "Error message"
}
```

---

**Simple, fast, and works with any DocType!**

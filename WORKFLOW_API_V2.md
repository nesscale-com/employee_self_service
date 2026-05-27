# ESS Workflow API v2

**Base path:** `/api/method/employee_self_service.mobile.v2.workflow.workflow`

This API replaces the v1 workflow endpoints. All field names, labels, and groupings are
driven by configuration stored in **ESS Workflow Settings** on the ERPNext side — the
mobile app never needs to hard-code field names for any doctype.

---

## Prerequisites (Admin Setup)

1. Open **ESS Workflow Settings** in ERPNext.
2. Tick **Enable Workflow In ESS**.
3. In the **ESS Workflow Documents** table, add a row for each doctype you want to expose
   (e.g. `Purchase Order`, `Material Request`).
   - The **Document** link only lists doctypes that already have an active **Workflow**
     configured in Frappe.
4. Click **Configure** on each row to open the Configure dialog:
   - **List View Fields** — pick up to 5 fields + labels. `workflow_state` is always
     appended automatically.
   - **Detail View Fields** — pick fields and group them into named sections (e.g.
     "Overview", "Financials"). Leave the Section column blank to default to "General".
5. Save the settings.

---

## Endpoints

### 1. `GET get_workflow_doctypes`

Returns the list of configured workflow doctypes and how many documents currently have
a pending action for the logged-in user.

**Use this to render the workflow home screen (doctype picker).**

```
GET /api/method/employee_self_service.mobile.v2.workflow.workflow.get_workflow_doctypes
```

**Response**
```json
{
  "message": "Workflow doctypes fetched successfully",
  "data": [
    {
      "doctype": "Purchase Order",
      "label": "Purchase Order",
      "pending_count": 5,
      "is_configured": true
    },
    {
      "doctype": "Material Request",
      "label": "Material Request",
      "pending_count": 3,
      "is_configured": true
    }
  ]
}
```

---

### 2. `GET get_document_list`

Returns a paginated list of workflow documents, shaped exactly by the saved
**List View Config**. Only documents where the current user has at least one
available action are returned.

**Use this to render the list screen for a doctype.**

```
GET /api/method/employee_self_service.mobile.v2.workflow.workflow.get_document_list
    ?doctype=Purchase Order
    &start=0
    &page_length=10
    &workflow_state=Pending Approval   (optional filter)
```

**Response**
```json
{
  "message": "Document list fetched successfully",
  "data": {
    "doctype": "Purchase Order",
    "total": 5,
    "start": 0,
    "page_length": 10,
    "has_more": false,
    "list_fields": [
      { "fieldname": "name",             "label": "Document No", "fieldtype": "Data",     "is_badge": false },
      { "fieldname": "supplier_name",    "label": "Supplier",    "fieldtype": "Data",     "is_badge": false },
      { "fieldname": "transaction_date", "label": "Date",        "fieldtype": "Date",     "is_badge": false },
      { "fieldname": "grand_total",      "label": "Total",       "fieldtype": "Currency", "is_badge": false },
      { "fieldname": "workflow_state",   "label": "Status",      "fieldtype": "Data",     "is_badge": true  }
    ],
    "documents": [
      {
        "name": "PUR-ORD-2026-00007",
        "doctype": "Purchase Order",
        "workflow_state": "Pending Approval",
        "fields": [
          { "fieldname": "name",             "label": "Document No", "fieldtype": "Data",     "is_badge": false, "value": "PUR-ORD-2026-00007" },
          { "fieldname": "supplier_name",    "label": "Supplier",    "fieldtype": "Data",     "is_badge": false, "value": "TechMart Supplies"  },
          { "fieldname": "transaction_date", "label": "Date",        "fieldtype": "Date",     "is_badge": false, "value": "2026-03-12"         },
          { "fieldname": "grand_total",      "label": "Total",       "fieldtype": "Currency", "is_badge": false, "value": 94500.0              },
          { "fieldname": "workflow_state",   "label": "Status",      "fieldtype": "Data",     "is_badge": true,  "value": "Pending Approval"   }
        ],
        "available_actions": ["Approve", "Reject"]
      }
    ]
  }
}
```

**Rendering hints**

| `fieldtype`       | Suggested render              |
|-------------------|-------------------------------|
| `Date`            | Format with locale            |
| `Datetime`        | Format with locale + time     |
| `Currency`        | Format with currency symbol   |
| `Check`           | Tick / cross icon             |
| `Data` + `is_badge: true` | Coloured status pill |
| anything else     | Plain text                    |

Use `list_fields` (the schema) to build column headers / labels once.
Use each document's `fields` array to render row values in the same order.

---

### 3. `GET get_document_detail`

Returns a single document shaped by the **Detail View Config** (sections + fields).

**Use this to render the detail / approval screen.**

```
GET /api/method/employee_self_service.mobile.v2.workflow.workflow.get_document_detail
    ?doctype=Purchase Order
    &name=PUR-ORD-2026-00007
```

**Response**
```json
{
  "message": "Document detail fetched successfully",
  "data": {
    "name": "PUR-ORD-2026-00007",
    "doctype": "Purchase Order",
    "workflow_state": "Pending Approval",
    "available_actions": ["Approve", "Reject"],
    "sections": [
      {
        "label": "Overview",
        "fields": [
          { "fieldname": "name",             "label": "Document No", "fieldtype": "Data",     "is_badge": false, "value": "PUR-ORD-2026-00007" },
          { "fieldname": "workflow_state",   "label": "Status",      "fieldtype": "Data",     "is_badge": true,  "value": "Pending Approval"   },
          { "fieldname": "transaction_date", "label": "Date",        "fieldtype": "Date",     "is_badge": false, "value": "2026-03-12"         }
        ]
      },
      {
        "label": "Financials",
        "fields": [
          { "fieldname": "grand_total", "label": "Total Amount", "fieldtype": "Currency", "is_badge": false, "value": 94500.0 },
          { "fieldname": "net_total",   "label": "Net Total",    "fieldtype": "Currency", "is_badge": false, "value": 80000.0 }
        ]
      }
    ]
  }
}
```

**Rendering hints**
- Render each `sections[]` entry as a card/group with a heading.
- Each field in `sections[].fields` renders as a label-value row.
- `available_actions` drives the action buttons at the bottom of the screen.

---

### 4. `GET get_document_actions`

Returns the actions available to the current user for a specific document without
fetching any field data. Useful for a quick check before showing action buttons.

```
GET /api/method/employee_self_service.mobile.v2.workflow.workflow.get_document_actions
    ?doctype=Purchase Order
    &name=PUR-ORD-2026-00007
```

**Response**
```json
{
  "message": "Document actions fetched successfully",
  "data": {
    "doctype": "Purchase Order",
    "name": "PUR-ORD-2026-00007",
    "workflow_state": "Pending Approval",
    "available_actions": ["Approve", "Reject"]
  }
}
```

---

### 5. `POST apply_document_action`

Applies a workflow action to a document. Returns the updated state and any new
available actions after the transition.

```
POST /api/method/employee_self_service.mobile.v2.workflow.workflow.apply_document_action

Body (form-data or JSON):
  doctype  = "Purchase Order"
  name     = "PUR-ORD-2026-00007"
  action   = "Approve"
```

**Response (success)**
```json
{
  "message": "Action 'Approve' applied successfully",
  "data": {
    "doctype": "Purchase Order",
    "name": "PUR-ORD-2026-00007",
    "workflow_state": "Approved",
    "available_actions": []
  }
}
```

**Response (permission error)**
```json
{
  "http_status_code": 403,
  "message": "Not permitted to perform 'Approve' on Purchase Order"
}
```

---

## Suggested Mobile Flow

```
┌─────────────────────────────────────────┐
│  Workflow Home                          │
│  get_workflow_doctypes                  │
│                                         │
│  [ Purchase Order  (5 pending) ]        │
│  [ Material Request (3 pending) ]       │
└────────────────┬────────────────────────┘
                 │  tap doctype
┌────────────────▼────────────────────────┐
│  Document List                          │
│  get_document_list?doctype=...          │
│                                         │
│  [ PUR-ORD-2026-00007  Pending ... ]    │
│  [ PUR-ORD-2026-00008  Pending ... ]    │
└────────────────┬────────────────────────┘
                 │  tap document
┌────────────────▼────────────────────────┐
│  Document Detail                        │
│  get_document_detail?doctype=&name=     │
│                                         │
│  Overview                               │
│    Document No   PUR-ORD-2026-00007     │
│    Status        [ Pending Approval ]   │
│    Date          12 Mar 2026            │
│                                         │
│  Financials                             │
│    Total Amount  ₹ 94,500              │
│                                         │
│  [ Approve ]  [ Reject ]               │
└────────────────┬────────────────────────┘
                 │  tap action
┌────────────────▼────────────────────────┐
│  apply_document_action (POST)           │
│  → new workflow_state + actions shown   │
└─────────────────────────────────────────┘
```

---

## Backward Compatibility

The v1 endpoints (`approval/workflow.py`) are **not changed** and remain fully functional.
The v2 endpoints are additive — migrate screens one at a time.

| v1 endpoint                    | v2 replacement             |
|-------------------------------|----------------------------|
| `get_active_workflow_document` | `get_workflow_doctypes`    |
| `get_workflow_documents`       | `get_document_list`        |
| `get_actions`                  | `get_document_actions`     |
| `update_workflow_state`        | `apply_document_action`    |

---

## Error Codes

| HTTP Status | Meaning                                      |
|-------------|----------------------------------------------|
| 200         | Success                                      |
| 400         | Bad request (workflow disabled / not configured) |
| 403         | Permission denied                            |
| 404         | Document not found                           |
| 500         | Unhandled server error (see Error Log)       |

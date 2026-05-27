# ESS Workflow API v2

**Base path:** `/api/method/employee_self_service.mobile.v2.workflow.workflow`

This API replaces the v1 workflow endpoints. All field names, labels, and groupings are
driven by configuration stored in **ESS Workflow Settings** on the ERPNext side — the
mobile app never needs to hard-code field names for any doctype.

Every field descriptor carries Flutter-ready data:

| Key | Purpose |
|-----|---------|
| `type` | Flutter widget hint (see table below) |
| `value` | Pre-formatted display string — render directly |
| `raw` | Native Python value — for sorting / custom logic |
| `badge` | `{bg_color, text_color}` hex strings — only on badge fields |

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
     appended automatically as a badge.
   - **Detail View Fields** — pick fields and group them into named sections (e.g.
     "Overview", "Financials"). Leave the Section column blank to default to "General".
5. Optionally click **Fetch Workflow Documents** on the parent form to auto-populate all
   active workflow doctypes with sensible defaults (list view from `in_list_view` fields,
   detail view from mandatory fields).
6. Save the settings.

---

## Flutter Type System

| `type` value | Frappe fieldtype(s) | Suggested Flutter widget |
|---|---|---|
| `text` | Data, Small Text, Text, Select, Read Only | `Text` |
| `date` | Date | Format with locale → `Text` |
| `datetime` | Datetime | Format with locale + time → `Text` |
| `time` | Time | `Text` |
| `currency` | Currency | Format with currency symbol → `Text` |
| `decimal` | Float | `Text` |
| `integer` | Int | `Text` |
| `percent` | Percent | Append `%` → `Text` |
| `boolean` | Check | Renders as `"Yes"` / `"No"` in `value` |
| `link` | Link, Dynamic Link | `Text` (or tappable) |
| `badge` | Any field with `is_badge: true` | Coloured pill chip |
| `color` | Color | Colour swatch |
| `rating` | Rating | Star widget |
| `duration` | Duration | `Text` |

> **Note:** `value` is already formatted — you don't need to parse `raw` to display it.
> Use `raw` only for sorting, comparisons, or computations.

---

## Badge colours

Badge fields (where `is_badge: true`) include a `badge` object with hex colour strings:

```dart
// Dart: Color.fromARGB(0xff, int.parse(hex.substring(1, 3), radix: 16), ...)
// Or:   Color(int.parse(hex.replaceFirst('#', '0xff')))
Color bg   = Color(int.parse(badge['bg_color'].replaceFirst('#', '0xff')));
Color text = Color(int.parse(badge['text_color'].replaceFirst('#', '0xff')));
```

Common states:

| State | bg_color | text_color |
|---|---|---|
| Draft | `#F3F4F6` | `#6B7280` |
| Pending Approval | `#FEF3C7` | `#92400E` |
| Approved | `#D1FAE5` | `#065F46` |
| Rejected | `#FEE2E2` | `#991B1B` |
| Completed | `#DBEAFE` | `#1E40AF` |
| Cancelled | `#FEE2E2` | `#991B1B` |

---

## Action button styles

`available_actions` entries carry button styling:

| `style` | bg_color | Typical actions |
|---|---|---|
| `success` | `#22C55E` | Approve |
| `danger` | `#EF4444` | Reject, Cancel |
| `primary` | `#3B82F6` | Submit for Approval |
| `warning` | `#F59E0B` | Resubmit, Revise |
| `secondary` | `#6B7280` | Everything else |

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

    "schema": [
      { "fieldname": "name",              "label": "Document No", "type": "text",     "is_badge": false },
      { "fieldname": "supplier_name",     "label": "Supplier",    "type": "text",     "is_badge": false },
      { "fieldname": "transaction_date",  "label": "Date",        "type": "date",     "is_badge": false },
      { "fieldname": "grand_total",       "label": "Total",       "type": "currency", "is_badge": false },
      { "fieldname": "workflow_state",    "label": "Status",      "type": "badge",    "is_badge": true  }
    ],

    "documents": [
      {
        "name": "PUR-ORD-2026-00007",
        "doctype": "Purchase Order",
        "workflow_state": "Pending Approval",
        "badge": { "bg_color": "#FEF3C7", "text_color": "#92400E" },

        "fields": [
          { "fieldname": "name",             "label": "Document No", "type": "text",     "is_badge": false, "value": "PUR-ORD-2026-00007",  "raw": "PUR-ORD-2026-00007" },
          { "fieldname": "supplier_name",    "label": "Supplier",    "type": "text",     "is_badge": false, "value": "TechMart Supplies",    "raw": "TechMart Supplies"  },
          { "fieldname": "transaction_date", "label": "Date",        "type": "date",     "is_badge": false, "value": "12 Mar 2026",          "raw": "2026-03-12"         },
          { "fieldname": "grand_total",      "label": "Total",       "type": "currency", "is_badge": false, "value": "₹ 94,500.00",         "raw": 94500.0              },
          { "fieldname": "workflow_state",   "label": "Status",      "type": "badge",    "is_badge": true,  "value": "Pending Approval",     "raw": "Pending Approval",
            "badge": { "bg_color": "#FEF3C7", "text_color": "#92400E" } }
        ],

        "available_actions": [
          { "action": "Approve", "label": "Approve", "style": "success", "bg_color": "#22C55E", "text_color": "#FFFFFF" },
          { "action": "Reject",  "label": "Reject",  "style": "danger",  "bg_color": "#EF4444", "text_color": "#FFFFFF" }
        ]
      }
    ]
  }
}
```

**Rendering hints**
- Use `schema` (the field definitions array) to build column headers / labels once.
- Use each document's `fields` array to render row values in the same order.
- `badge` at the document root is the colour for the state chip in the list row.
- `fields[].badge` is the colour for an individual badge field (same data, different scope).

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
    "badge": { "bg_color": "#FEF3C7", "text_color": "#92400E" },

    "available_actions": [
      { "action": "Approve", "label": "Approve", "style": "success", "bg_color": "#22C55E", "text_color": "#FFFFFF" },
      { "action": "Reject",  "label": "Reject",  "style": "danger",  "bg_color": "#EF4444", "text_color": "#FFFFFF" }
    ],

    "sections": [
      {
        "label": "Overview",
        "fields": [
          { "fieldname": "name",             "label": "Document No", "type": "text", "is_badge": false, "value": "PUR-ORD-2026-00007", "raw": "PUR-ORD-2026-00007" },
          { "fieldname": "workflow_state",   "label": "Status",      "type": "badge","is_badge": true,  "value": "Pending Approval",   "raw": "Pending Approval",
            "badge": { "bg_color": "#FEF3C7", "text_color": "#92400E" } },
          { "fieldname": "transaction_date", "label": "Date",        "type": "date", "is_badge": false, "value": "12 Mar 2026",        "raw": "2026-03-12" }
        ]
      },
      {
        "label": "Financials",
        "fields": [
          { "fieldname": "grand_total", "label": "Total Amount", "type": "currency", "is_badge": false, "value": "₹ 94,500.00", "raw": 94500.0 },
          { "fieldname": "net_total",   "label": "Net Total",    "type": "currency", "is_badge": false, "value": "₹ 80,000.00", "raw": 80000.0 }
        ]
      }
    ]
  }
}
```

**Rendering hints**
- Render each `sections[]` entry as a card/group with a section heading.
- Each field in `sections[].fields` renders as a label-value row.
- `available_actions` drives the styled action buttons at the bottom of the screen.
- Render each action button using `bg_color` / `text_color` directly — no style mapping needed.

---

### 4. `GET get_document_actions`

Returns the actions available to the current user for a specific document without
fetching any field data. Useful for a quick refresh of button state.

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
    "badge": { "bg_color": "#FEF3C7", "text_color": "#92400E" },
    "available_actions": [
      { "action": "Approve", "label": "Approve", "style": "success", "bg_color": "#22C55E", "text_color": "#FFFFFF" },
      { "action": "Reject",  "label": "Reject",  "style": "danger",  "bg_color": "#EF4444", "text_color": "#FFFFFF" }
    ]
  }
}
```

---

### 5. `POST apply_document_action`

Applies a workflow action to a document. Returns the updated state and the new
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
    "badge": { "bg_color": "#D1FAE5", "text_color": "#065F46" },
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
│    Total Amount  ₹ 94,500.00           │
│                                         │
│  [ Approve ]  [ Reject ]               │
└────────────────┬────────────────────────┘
                 │  tap action
┌────────────────▼────────────────────────┐
│  apply_document_action (POST)           │
│  → new workflow_state + badge + actions │
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

**Breaking changes from any earlier v2 draft:**

| Old key | New key | Location |
|---|---|---|
| `list_fields` | `schema` | `get_document_list` response root |
| `available_actions: ["Approve"]` (string array) | `available_actions: [{action, label, style, bg_color, text_color}]` (object array) | All endpoints |
| *(absent)* | `badge: {bg_color, text_color}` | Document root in all responses |
| `fieldtype` | `type` | Field descriptor |

---

## Error Codes

| HTTP Status | Meaning                                      |
|-------------|----------------------------------------------|
| 200         | Success                                      |
| 400         | Bad request (workflow disabled / not configured) |
| 403         | Permission denied                            |
| 404         | Document not found                           |
| 500         | Unhandled server error (see Error Log)       |

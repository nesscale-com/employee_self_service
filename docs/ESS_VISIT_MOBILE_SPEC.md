# ESS Visit — Mobile (Flutter) Implementation Spec

> Audience: the Flutter agent implementing the **ESS Visit** feature in the ESS mobile app.
> Backend repo of record: `employee_self_service`. This doc describes the data model, the
> common v2 APIs to use, and the three screens to build (List → Detail → Create/Edit),
> matching the existing mobile patterns.

---

## 1. Context

ESS already has a **basic "Visit"** feature wired to the legacy `Visit` doctype
(`mobile/v1/visit.py`). We are **replacing it** with a richer **`ESS Visit`** doctype.

Do **not** build new per-doctype endpoints. ESS Visit must be driven entirely by the
**common v2 CRUD + link APIs** (see §3). Keep the legacy v1 visit code untouched.

---

## 2. Data model — `ESS Visit`

DocType: **`ESS Visit`** · autoname `EVISIT.#####` (server-generated, never sent by client).

| Field | Type | Notes for app |
|---|---|---|
| `customer_type` | Select `Existing` / `New` | default `Existing`, **required** |
| `customer` | Link → **Customer** | shown/required only when `customer_type == Existing`. Use **link option API**. |
| `customer_name` | Data | required only when `customer_type == New`; auto-fetched from `customer` otherwise |
| `status` | Select `Pending` / `In Progress` / `Completed` | default `Pending`, **required**. Drives the tabs + lifecycle. |
| `visit_type` | Link → **Visit Type** | **required**. Use **link option API**. |
| `description` | Small Text | **required** |
| `visit_start_time` | Datetime | set when visit is started |
| `visit_stop_time` | Datetime | set when visit is completed |
| `visit_start_location` | Geolocation (GeoJSON) | **sent at Start** — used for customer auto geo-tag (see §6.5) |
| `user_remarks` | Small Text | optional |
| `customer_signature` | Signature | base64 PNG **data-URI string** stored directly on the field |
| `visit_proof` | Table → **Visit Proof** | child rows: `{ "attachment": "<file_url>" }` |
| `employee` | Link → Employee | server-managed (see §7) — app never sends it |
| `user` | Link → User | server-managed, fetched from `employee.user_id` |

> The doctype also has `visit_stop_location` (Geolocation) and `auto_created_from_rule`
> fields. These are **not used by the mobile app** — do not read, render, or send them.
> `visit_start_location` is the only location the app sends, and only at Start.

**Child table — `Visit Proof`**: single field `attachment` (Attach). One row per uploaded
proof image. Send as a list inside the ESS Visit `data` payload.

**Geolocation format**: Frappe stores Geolocation as a GeoJSON `FeatureCollection` string.
For a single point send:
```json
{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},
"geometry":{"type":"Point","coordinates":[<lng>,<lat>]}}]}
```
Note GeoJSON order is **[longitude, latitude]**.

---

## 3. Common v2 APIs (use these — do not write new ones)

Standard response envelope for every call:
```json
{ "http_status_code": 200, "message": "…", "data": <payload> }
```
On error, `http_status_code` is 4xx/5xx and `message` holds the reason. Always branch on
`http_status_code`.

### 3.1 CRUD — `employee_self_service.mobile.v2.common.document`

| Op | Method · endpoint | Params |
|---|---|---|
| Create | POST `…document.create_document` | `doctype`, `data` (JSON object) |
| Read   | GET  `…document.get_document` | `doctype`, `name` |
| Update | POST `…document.update_document` | `doctype`, `name`, `data` (JSON object) |
| Delete | POST `…document.delete_document` | `doctype`, `name` |
| List   | GET  `…document.get_document_list` | `doctype`, `fields`, `filters`, `order_by`, `start`, `page_length` |

- `create`/`update`/`get` return the saved document object in `data` (default/meta fields stripped).
- `list` returns a **plain array** of records in `data` (no pagination wrapper). Paginate with
  `start` / `page_length`; `fields` and `filters` accept JSON (Frappe filter syntax).
- All run under the **caller's permissions** (403 if not allowed).

### 3.2 Link option picker — `employee_self_service.mobile.v2.common.get_link_option_list`
GET · params `doctype`, `fields` (default `["name"]`), `filters`, `start`, `page_length` (default 20).
Use for the **Customer** and **Visit Type** pickers, with server-side search via `filters`
(e.g. `[["customer_name","like","%acme%"]]`) and infinite-scroll via `start`/`page_length`.

### 3.3 Select options — `employee_self_service.mobile.v2.common.get_option_list`
GET · params `doctype`, `field_name`. Use to fetch `status` / `customer_type` options instead of
hardcoding (optional but preferred).

### 3.4 Attachments — `employee_self_service.mobile.v2.common.*`
- `upload_documents` — POST multipart: `reference_doctype`, `reference_docname`, `file`, `is_private`.
  Returns `{name, file_url, file_name, is_private}`. Requires the doc to already exist.
- `get_attachments` — GET: `reference_doctype`, `reference_name`.
- `delete_file` — POST: `file_name`.

### 3.5 Settings — `employee_self_service.mobile.v2.settings.get_field_staff_settings`
GET · returns the single **ESS Field Staff Settings**. Relevant flags for this feature:
- `visit_required_geofencing` (0/1)
- `allowed_radius` (meters, int)

---

## 4. Screen 1 — Visit List (two tabs)

A tabbed list screen, reusing the app's existing list/card pattern.

- **Tab A — Pending**: `filters = [["status","in",["Pending","In Progress"]]]`
- **Tab B — Completed**: `filters = [["status","=","Completed"]]`

Fetch via `get_document_list`:
```
doctype=ESS Visit
fields=["name","customer_name","customer_type","visit_type","status",
        "description","visit_start_time","visit_stop_time"]
filters=<tab filter>
order_by="modified desc"
start=<page*page_length>  page_length=20
```
Card shows: customer_name (fallback to `customer`), visit_type, status badge, description,
and start/stop time when present. Tapping a card → **Detail** screen. FAB → **Create** screen.
Implement pagination by incrementing `start`; list returns a bare array, so "has more" =
"returned count == page_length".

---

## 5. Screen 2 — Visit Detail

Load with `get_document(doctype="ESS Visit", name=<EVISIT-id>)`. Mirror the existing detail-view
layout. Render all fields read-only, plus:

- **Status badge** + lifecycle action button (see §6): "Start Visit" / "Complete Visit".
- **Signature**: render `customer_signature` data-URI as an image.
- **Visit proofs**: thumbnails from `visit_proof[].attachment` (also `get_attachments` if needed).
- **Edit** action → Edit screen (allowed while not `Completed`; confirm rule in §6).

---

## 6. Screens 3 & 4 — Create / Edit + Visit lifecycle

Reuse the existing create/edit form pattern. Same form, different mode (Create = new, Edit =
prefill from `get_document`).

### 6.1 Create form fields
- `customer_type` (segmented Existing/New, default Existing)
- if Existing → `customer` (link picker, required) ; else → `customer_name` (text, required)
- `visit_type` (link picker, required)
- `description` (multiline, required)
- `user_remarks` (multiline, optional)

On submit → `create_document`:
```json
{ "doctype": "ESS Visit",
  "data": { "customer_type":"Existing", "customer":"CUST-0001",
            "visit_type":"Sales Call", "description":"…", "status":"Pending" } }
```
Do **not** send `name`, `employee`, `user` (server-managed — see §7).

### 6.2 Edit
`update_document(doctype="ESS Visit", name, data={…changed fields…})`. Never send `name`/`doctype`
inside `data`. Block editing once `status == Completed` (read-only detail only) unless product
says otherwise.

### 6.3 Lifecycle (status transitions)
```
Pending ──Start Visit──▶ In Progress ──Complete Visit──▶ Completed
```

**Geofencing applies only to existing customers.** When `customer_type == "New"`, **skip the
geofencing validation entirely** — a new customer has no tagged reference point yet.

**Start Visit** (from Pending):
1. Read current GPS location.
2. If `visit_required_geofencing == 1` **and** `customer_type == "Existing"`: compute distance
   from current location to the **customer's tagged location**; if `> allowed_radius` meters,
   **block** with a clear error ("You are N m away; must be within `allowed_radius` m"). See
   §6.4 for the reference point.
3. `update_document` with: `status="In Progress"`, `visit_start_time=<now>`,
   `visit_start_location=<GeoJSON point>` (always send it — drives the auto geo-tag in §6.5).

**Complete Visit** (from In Progress):
1. Read current GPS location and apply the same geofence check if enabled
   (again, only when `customer_type == "Existing"`).
2. Collect completion data: `user_remarks`, `customer_signature` (data-URI), and proof images.
3. Upload each proof image, then set child rows, e.g.:
   `data.visit_proof = [{"attachment": "<file_url>"}, …]`.
4. `update_document` with: `status="Completed"`, `visit_stop_time=<now>`,
   `user_remarks`, `customer_signature`, `visit_proof`.

> Recommended ordering for proofs/signature: the visit doc already exists (created as Pending),
> so use `upload_documents` with `reference_docname=<EVISIT-id>` to store proof files, take the
> returned `file_url`, and put it into `visit_proof` rows on the completion `update_document`.
> `customer_signature` needs no upload — send the base64 data-URI string directly.

### 6.4 Geofencing reference point
The geofencing radius is measured from the customer's **`Customer Location`** record
(`latitude`/`longitude`). Read it via
`employee_self_service.mobile.v2.common.get_customer_location?customer=<id>` → returns
`{name, latitude, longitude}` (or empty when not tagged yet). For `customer_type == New`
geofencing is **skipped** (§6.3).

### 6.5 Customer auto geo-tag (backend — already implemented)
This is handled server-side; the app's only job is to **send `visit_start_location` at Start**.

On ESS Visit save, when **ESS Field Staff Settings → `customer_geo_tagging_auto_based_on` ==
`Visit`** and the **existing** customer has **no `Customer Location`** yet, the backend creates
one from the visit's `visit_start_location` point. It runs only once per customer (never
overwrites an existing location). Consequence for the app: the **first** visit to a customer has
no reference point, so geofencing is naturally not enforced on it; subsequent visits geofence
against the location captured on that first visit.

---

## 7. Backend status

**Resolved (already implemented in the backend):**
1. ✅ **`employee` / `user` defaulting.** Handled server-side and securely. `ESS Visit` now
   resolves `employee` from the **session user** (`before_insert` + `validate`) when the client
   doesn't send it, and fills `user` from the employee. The mobile app should **not** send
   `employee`/`user` — they are derived from the authenticated session, so the client cannot
   spoof visit ownership.
2. ✅ **Settings endpoint fixed.** `get_field_staff_settings` now reads the correct
   `"ESS Field Staff Settings"` single doctype.
3. ✅ **Geofencing for New customers** is skipped (see §6.3 / §6.4) — app-side rule.
4. ✅ **List scoping.** No per-user scoping — the list shows **all** documents returned by
   `get_document_list` (subject only to standard Frappe permissions). No client-side owner filter.
5. ✅ **Geofencing reference** is the `Customer Location` doctype; read via `get_customer_location`
   (§6.4). The setting `customer_geo_tagging_auto_based_on` is now **Visit-only** (Sales Order /
   Both removed).
6. ✅ **Customer auto geo-tag** on first visit implemented in the `ESS Visit` controller (§6.5).

**Still to confirm:**
- **Tab definition** — "Pending" tab assumed to include `In Progress` (confirm with product).

---

## 8. Acceptance checklist

- [ ] List screen with Pending / Completed tabs, paginated via `get_document_list`.
- [ ] Customer & Visit Type pickers use `get_link_option_list` with search + paging.
- [ ] Create flow posts to `create_document` (status defaults Pending).
- [ ] Detail screen renders via `get_document` incl. map, signature, proofs.
- [ ] Edit flow uses `update_document`; locked after Completed.
- [ ] Start/Complete lifecycle sets times and status correctly.
- [ ] Geofencing enforced only when `visit_required_geofencing == 1`, using `allowed_radius`.
- [ ] Proof images uploaded and linked in `visit_proof`; signature stored as data-URI.
- [ ] All error envelopes (`http_status_code` != 200) surfaced to the user.

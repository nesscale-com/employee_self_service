# Pollen Issue Mobile API Documentation

This document describes all the available APIs for the Pollen Issue management system in the ESS mobile app.

## Base URL
All APIs are accessible via:
```
/api/method/pollenkisan.mobile.v1.issue.<function_name>
```

## Authentication
All APIs require authentication. Include the session token in the headers or use Frappe's authentication mechanism.

## Response Format
All APIs return responses in the following format:
```json
{
    "http_status_code": 200,
    "message": "Success message",
    "data": {...}
}
```

Error responses:
```json
{
    "http_status_code": 500,
    "message": "Error message",
    "data": []
}
```

## Available APIs

### 1. Create Issue
**Endpoint:** `create`
**Method:** POST
**Description:** Creates a new Pollen Issue

**Parameters:**
- `subject` (required): Issue title
- `description` (required): Detailed description
- `issue_type` (required): Type of issue (from Pollen Issue Type)
- `customer` (optional): Customer name
- `priority` (optional): Priority level (Low/Medium/High/Urgent, default: Medium)

**Response:**
```json
{
    "issue_id": "ISSUE-001",
    "status": "Pending",
    "assigned_to": "user@example.com",
    "priority": "Medium",
    "date": "2024-01-01"
}
```

### 2. Update Issue
**Endpoint:** `update`
**Method:** POST
**Description:** Updates an existing issue (only assignee or System Manager can update)

**Parameters:**
- `issue_id` (required): Issue ID to update
- `comment` (optional): Add a comment
- `priority` (optional): Update priority
- `description` (optional): Update description
- `status` (optional): Update status (except 'Closed' - use update_status for that)

**Response:**
```json
{
    "issue_id": "ISSUE-001",
    "status": "In Progress",
    "priority": "High",
    "current_assignee": "user@example.com"
}
```

### 3. Get Issue List
**Endpoint:** `get_issue_list`
**Method:** GET
**Description:** Retrieves paginated list of issues with two types: pending (assigned to current user) and all issues

**Parameters:**
- `start` (optional): Starting index for pagination (default: 0)
- `page_length` (optional): Number of items per page (default: 10)
- `filters` (optional): JSON string of additional filters
- `list_type` (optional): "pending" or "all" (default: "all")

**Examples:**
```
# Get pending issues for current user
GET /api/method/pollenkisan.mobile.v1.issue.get_issue_list?list_type=pending

# Get all issues with pagination
GET /api/method/pollenkisan.mobile.v1.issue.get_issue_list?start=0&page_length=20&list_type=all

# Get issues with filters
GET /api/method/pollenkisan.mobile.v1.issue.get_issue_list?filters={"status":"In Progress"}
```

**Response:**
```json
{
    "issues": [
        {
            "name": "ISSUE-001",
            "subject": "Login Problem",
            "customer": "CUST-001",
            "customer_name": "ABC Company",
            "issue_type": "Technical",
            "status": "In Progress",
            "current_assignee": "user@example.com",
            "date": "2024-01-01",
            "priority": "High",
            "creation": "2024-01-01 10:00:00",
            "modified": "2024-01-01 11:30:00"
        }
    ],
    "total_count": 50,
    "current_page": 1,
    "has_next": true
}
```

### 4. Get Issue Details
**Endpoint:** `get_issue_details`
**Method:** GET
**Description:** Retrieves complete details of a specific issue including comments

**Parameters:**
- `name` (required): Issue name/ID

**Response:**
```json
{
    "name": "ISSUE-001",
    "subject": "Login Problem",
    "description": "User cannot login to the system",
    "customer": "CUST-001",
    "issue_type": "Technical",
    "status": "In Progress",
    "current_assignee": "user@example.com",
    "priority": "High",
    "date": "2024-01-01",
    "resolution_date": null,
    "resolution_comment": null,
    "assignment_history": [...],
    "comments": [
        {
            "name": "COMM-001",
            "comment_type": "Comment",
            "content": "Working on this issue",
            "owner": "user@example.com",
            "creation": "2024-01-01 11:00:00",
            "comment_by": "John Doe"
        }
    ]
}
```

### 5. Update Issue Status
**Endpoint:** `update_status`
**Method:** POST
**Description:** Updates issue status with optional comment (only assignee or System Manager)

**Parameters:**
- `issue_id` (required): Issue ID
- `status` (required): New status (Pending/In Progress/Closed)
- `comment` (optional): Comment about status change

**Response:**
```json
{
    "issue_id": "ISSUE-001",
    "status": "Closed",
    "old_status": "In Progress",
    "resolution_date": "2024-01-01 15:00:00"
}
```

### 6. Forward Issue
**Endpoint:** `forward_issue`
**Method:** POST
**Description:** Forward issue to another user (only assignee or System Manager)

**Parameters:**
- `issue_id` (required): Issue ID
- `to_user` (required): User email to forward to
- `comment` (optional): Comment about forwarding

**Response:**
```json
{
    "issue_id": "ISSUE-001",
    "from_user": "user1@example.com",
    "to_user": "user2@example.com",
    "current_assignee": "user2@example.com",
    "status": "In Progress"
}
```

### 7. Backward Issue
**Endpoint:** `backward_issue`
**Method:** POST
**Description:** Move issue back to previous assignee (only assignee or System Manager)

**Parameters:**
- `issue_id` (required): Issue ID
- `comment` (optional): Comment about moving back

**Response:**
```json
{
    "issue_id": "ISSUE-001",
    "current_assignee": "previous_user@example.com",
    "status": "In Progress"
}
```

### 8. Get Assignment History
**Endpoint:** `get_assignment_history`
**Method:** GET
**Description:** Retrieves assignment history for an issue

**Parameters:**
- `issue_id` (required): Issue ID

**Response:**
```json
[
    {
        "action": "forward",
        "from_user": "user1@example.com",
        "from_user_name": "John Doe",
        "to_user": "user2@example.com",
        "to_user_name": "Jane Smith",
        "note": "Forwarding to specialist",
        "timestamp": "2024-01-01 12:00:00"
    }
]
```

### 9. Get Issue Statistics
**Endpoint:** `get_issue_statistics`
**Method:** GET
**Description:** Get dashboard statistics for current user

**Response:**
```json
{
    "total_issues": 100,
    "my_pending_issues": 5,
    "my_total_issues": 25,
    "closed_issues": 60,
    "in_progress_issues": 30,
    "pending_issues": 10,
    "my_high_priority": 2,
    "my_urgent_priority": 1
}
```

### 10. Search Issues
**Endpoint:** `search_issues`
**Method:** GET
**Description:** Search issues by subject, description, customer name, or issue ID

**Parameters:**
- `search_term` (required): Text to search for
- `start` (optional): Starting index for pagination (default: 0)
- `page_length` (optional): Number of items per page (default: 10)

**Response:**
```json
{
    "issues": [...],
    "total_count": 15,
    "search_term": "login",
    "current_page": 1,
    "has_next": false
}
```

## Dropdown/Option APIs

### 11. Get Issue Types
**Endpoint:** `get_issue_type_list`
**Method:** GET
**Description:** Get all available issue types

**Response:**
```json
[
    {
        "name": "Technical",
        "issue_type": "Technical",
        "default_assignee": "tech@example.com"
    }
]
```

### 12. Get Customer List
**Endpoint:** `get_customer_list`
**Method:** GET
**Description:** Get all active customers

**Response:**
```json
[
    {
        "name": "CUST-001",
        "customer_name": "ABC Company",
        "customer_group": "Corporate"
    }
]
```

### 13. Get User List
**Endpoint:** `get_user_list`
**Method:** GET
**Description:** Get all active users for assignment

**Response:**
```json
[
    {
        "name": "user@example.com",
        "full_name": "John Doe",
        "email": "user@example.com"
    }
]
```

### 14. Get Issue Options (Combined)
**Endpoint:** `get_issue_options`
**Method:** GET
**Description:** Get all dropdown options in one API call

**Response:**
```json
{
    "issue_types": [...],
    "customers": [...],
    "users": [...],
    "priorities": ["Low", "Medium", "High", "Urgent"],
    "statuses": ["Pending", "In Progress", "Closed"]
}
```

## Mobile App Integration Guide

### Tab Implementation
1. **Pending Tab:** Use `get_issue_list?list_type=pending`
2. **All Issues Tab:** Use `get_issue_list?list_type=all`

### Dashboard Integration
Use `get_issue_statistics` to show:
- My pending issues count
- Priority issues requiring attention
- Overall statistics

### Issue Management Flow
1. **Create Issue:** Use `get_issue_options` → `create`
2. **View Issues:** Use `get_issue_list` → `get_issue_details`
3. **Update Issue:** Use `update` or `update_status`
4. **Forward/Backward:** Use `forward_issue` or `backward_issue`
5. **Search:** Use `search_issues`

### Error Handling
All APIs return consistent error responses with appropriate HTTP status codes and descriptive messages.

### Permissions
- Users can only update issues assigned to them
- System Managers have full access
- Issue creators can view their issues
- Forward/backward operations respect assignment hierarchy

## Example Usage

### Creating an Issue
```javascript
const response = await fetch('/api/method/pollenkisan.mobile.v1.issue.create', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-Frappe-CSRF-Token': 'your-csrf-token'
    },
    body: JSON.stringify({
        subject: 'Login Issue',
        description: 'Cannot access the system',
        issue_type: 'Technical',
        customer: 'CUST-001',
        priority: 'High'
    })
});
```

### Getting Pending Issues
```javascript
const response = await fetch('/api/method/pollenkisan.mobile.v1.issue.get_issue_list?list_type=pending&page_length=20');
const data = await response.json();
```

### Forwarding an Issue
```javascript
const response = await fetch('/api/method/pollenkisan.mobile.v1.issue.forward_issue', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        issue_id: 'ISSUE-001',
        to_user: 'specialist@example.com',
        comment: 'Forwarding to technical specialist'
    })
});
```
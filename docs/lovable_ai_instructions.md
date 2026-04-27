# LOVABLE AI FRONTEND instructions

## Project: Project Expense & Claim Tracker (MYR)

You are building a **frontend-only application in Lovable** for a Project Expense & Claim Tracker system. Backend is assumed to be a separate FastAPI service, so you MUST design the frontend to be API-driven with clean integration points.

The UI must be modular, scalable, and production-structured, but backend implementation is NOT part of your scope.

---

## 1. CORE PRODUCT CONTEXT

This application manages:

### Entities

- Projects
- Expenses (from manual entry + PDF ingestion)
- Income (manual only)

### Key Rules

- Currency is primarily MYR
- Expenses can be toggled as:
  - `claimed`
  - `not claimed`
- Income is ALWAYS manually entered (never derived from PDF)
- PDF upload ONLY generates expense candidates for review

---

## 2. REQUIRED PAGES

## (1) Dashboard Page

### Purpose

High-level financial summary per project.

### UI Layout

For each project card:

- Project name
- Total Income
- Total Expenses
- Net Position (Income - Expenses)
- Total Claimed Expenses
- Total Unclaimed Expenses

### API Call (placeholder)

```ts
GET /api/projects/summary
```

### Expected response shape

```ts
[
  {
    project_id,
    project_name,
    total_income,
    total_expenses,
    net_position,
    total_claimed,
    total_unclaimed
  }
]
```

---

## (2) Projects Page

### Features

- List projects
- Create project
- Edit project
- View project detail

### Project fields

- name
- description
- start_date
- end_date
- budget
- status

### API Calls

```ts
GET    /api/projects
POST   /api/projects
PUT    /api/projects/:id
DELETE /api/projects/:id
```

### Project Detail API

```ts
GET /api/projects/:id
```

---

## (3) Expenses Page

### Features

- Table of ALL expenses (cross-project)
- Filters:

  - project
  - date range
  - category
  - claim status
- Toggle claimed/unclaimed inline
- Edit expense
- Add manual expense

### Table columns

- project
- date
- vendor/description
- amount
- currency
- category
- is_claimed (toggle)
- claimed_date
- notes
- source (manual/pdf)

---

### API Calls

```ts
GET    /api/expenses
POST   /api/expenses
PUT    /api/expenses/:id
DELETE /api/expenses/:id
```

### Toggle claimed status

```ts
PATCH /api/expenses/:id/claim-toggle
```

Bulk toggle:

```ts
PATCH /api/expenses/bulk-claim-toggle
```

---

## (4) Income Page

### Features

- List income entries (per project)
- Create / Edit / Delete income
- Must always be manually entered

### API Calls

```ts
GET    /api/income?project_id=
POST   /api/income
PUT    /api/income/:id
DELETE /api/income/:id
```

---

## (5) PDF Import Page

### Workflow

1. Select Project
2. Upload PDF
3. System parses transactions
4. Show preview table (editable)
5. User confirms → expenses saved

---

### Step 1: Upload PDF

```ts
POST /api/pdf/upload
```

Response:

```ts
{
  upload_id,
  parsed_transactions: [
    {
      date,
      description,
      amount,
      currency,
      category_suggestion
    }
  ]
}
```

---

### Step 2: Confirm Import

```ts
POST /api/pdf/confirm
```

Request:

```ts
{
  upload_id,
  project_id,
  transactions: [...]
}
```

---

## 3. GLOBAL UI REQUIREMENTS

## Navigation

Sidebar with:

- Dashboard
- Projects
- Expenses
- Income
- PDF Import

---

## UX rules

- All forms must be modal or dedicated pages
- Loading + error states required everywhere

---

## 4. FRONTEND ARCHITECTURE REQUIREMENTS

You MUST structure the frontend as API-driven components.

### Required structure

```
/api
  client.ts
  projects.ts
  expenses.ts
  income.ts
  pdf.ts

/components
/pages
/hooks
/types
```

---

## 5. REQUIRED API CLIENT TEMPLATE (IMPORTANT)

You MUST implement a reusable API wrapper so backend integration is trivial.

### base API client

```ts
// /api/client.ts

const BASE_URL = "http://localhost:8000/api";

export async function apiRequest<T>(
  endpoint: string,
  method: string = "GET",
  body?: any
): Promise<T> {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method,
    headers: {
      "Content-Type": "application/json"
    },
    body: body ? JSON.stringify(body) : undefined
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.message || "API Error");
  }

  return res.json();
}
```

---

### Example usage pattern (MANDATORY)

```ts
import { apiRequest } from "./client";

export const getProjects = () =>
  apiRequest("/projects");

export const createProject = (data) =>
  apiRequest("/projects", "POST", data);
```

---

### REQUIRED FRONTEND BEHAVIOR

- Every API call MUST use this wrapper
- No direct fetch() calls outside this abstraction
- All endpoints must be easy to replace by changing BASE_URL only

---

## 6. PDF PARSING UX REQUIREMENTS

### Important constraints

- PDF data is NEVER auto-saved
- User MUST review parsed transactions
- User can:

  - edit amount
  - edit description
  - remove rows
  - assign category

### UI pattern

- Table with inline editing
- “Confirm Import” button
- “Cancel” returns to upload

---

## 7. DATA DISPLAY RULES

- All money displayed in RM format
- Negative values should be visually distinct
- Claimed expenses must have:

  - visual indicator (badge or color)
- Unclaimed must be clearly visible for tracking

---

## 8. PLACEHOLDERS / BACKEND INTEGRATION RULE

Wherever backend is required:

- Add clear TODO comments:

```ts
// TODO: connect to backend endpoint: /expenses/:id/claim-toggle
```

- Do NOT mock full backend logic
- Only mock UI state where needed

---

## 9. OUT OF SCOPE (DO NOT BUILD)

- Authentication
- Role-based access control
- Multi-user collaboration
- Complex approval workflows
- Payment processing

---

## 10. DESIGN EXPECTATIONS

- Clean dashboard style
- Minimal gradients
- Focus on simplicity and readability over decoration

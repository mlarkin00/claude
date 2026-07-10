---
name: syncing-emails-to-sheets
description: Use when the user wants to synchronize customer emails to a tracking spreadsheet. This skill retrieves emails with label `_a/Customers/Agentic` from the last 7 days and updates the specified Google Sheet.
---

# Syncing Emails to Sheets

This skill automates the process of extracting customer engagement data from Gmail and updating a Google Sheet.

## Context
- **Source**: Gmail threads labeled `_a/Customers/Agentic` from the last 7 days.
- **Destination**: Google Sheet `https://docs.google.com/spreadsheets/d/19FLU3E9LQHDKlOZSqZkaTzlXwfdsMtY2K13fWxGbFNM/edit?resourcekey=0-cmaPUDv-6j5qG_EsknLkgg&gid=1163589664#gid=1163589664`, tab `Engagement`.

## Instructions

### 1. Retrieve Emails
- Search for emails in Gmail with the query `label:_a/Customers/Agentic`.
- Filter for threads that have messages from the last 7 days.

### 2. Extract Information
For each matching thread, extract the following:
- **Thread Title**: The Subject of the first email in the thread.
- **Customer**: Derive the customer name from the subject, email addresses, or message body.
- **Date**: The date of the latest email in the thread.
- **Action Items**: Any action items mentioned in the thread. Format these as **bullet points**.
- **Summary**: A concise summary of the thread content.

### 3. Update Spreadsheet
- Open the spreadsheet and navigate to the `Engagement` tab.
- Review existing rows where the `Type` column (Column C) has the value "Email".
- Identify matching rows based on the combination of **Customer** and **Notes / Docs** (which contains the thread title/subject).
- **If a matching row exists**: Update the row with the new Date, Action Items, and Summary.
- **If no matching row exists**: Append a new row with the extracted data, setting `Type` to "Email".

## Gotchas & Anti-Patterns

| Excuse | Reality |
| :--- | :--- |
| "I can't find the label." | Verify the label name. Gmail might display it differently than the API name. |
| "I'll just add a new row without checking." | You MUST check for existing engagements to avoid duplicates. |
| "The action items are short, I'll use a list." | Action items MUST always be formatted as bullet points. |

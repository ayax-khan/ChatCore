# ChatCore User Manual

## Getting Started

### 1. Create an Account
1. Go to `https://app.chatcore.dev/register`
2. Enter your email, password, and business name
3. Verify your email (check inbox)
4. Log in at `https://app.chatcore.dev/login`

### 2. Add Your Website
1. From Dashboard, click **Add Site**
2. Enter your website URL and name
3. Click **Save** — ChatCore will crawl your site automatically
4. Wait for the crawl to complete (status changes to "indexed")

### 3. Install Chat Widget
Add this snippet before `</body>` on your website:
```html
<script src="https://cdn.chatcore.dev/widget.js" data-site-id="YOUR_SITE_ID"></script>
```

### 4. Customize Widget
Go to **Settings > Widget** to customize:
- Colors (primary, background, text)
- Position (bottom-right, bottom-left)
- Greeting message
- Avatar
- Brand name

### 5. Monitor Analytics
Dashboard shows:
- Daily Active Users (DAU)
- Total conversations
- Top questions asked
- AI cost breakdown
- Error rates

### 6. Manage Team
- **Settings > Team**: Invite members, assign roles (admin, editor, viewer)
- Each role has different permissions

### 7. Billing
- **Settings > Billing**: View current plan, upgrade, add payment method
- Plans: Free (1 site, 500 queries/mo), Starter (3 sites, 5000 queries/mo), Professional (10 sites, 50000 queries/mo), Enterprise (custom)

## Features

### Chat Widget
- Floating button on your website
- Real-time streaming responses
- Suggested questions
- Rating/thumbs feedback
- Lead capture form

### Knowledge Base
- Auto-crawl your website
- Support for PDF, DOCX, CSV files
- Manual re-crawl option
- View indexed pages and chunks

### Analytics Dashboard
- Usage metrics (sessions, messages, DAU)
- Top questions asked
- Error logs
- Cost breakdown by AI model
- Daily trends

### Team Management
- Invite team members via email
- Assign roles: Admin, Editor, Viewer
- Deactivate/remove users
- Audit log of all actions

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Widget not showing | Check site ID, clear cache, verify script tag |
| Crawl stuck | Re-crawl from dashboard, check robots.txt |
| Wrong answers | Re-crawl site, check indexed content |
| Rate limited | Upgrade plan or wait for reset |
| Email not received | Check spam, verify email in settings |

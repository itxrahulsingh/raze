# Custom Branding & Theming Guide

**Customize RAZE for your industry, company, or brand in 5 minutes.**

---

## Quick Configuration

### 1. Edit `.env` File

```bash
nano .env
```

Add these branding variables (or use defaults):

```bash
# ─── Branding ───────────────────────────────────────────
BRAND_NAME=YourCompanyName              # e.g., "TechCorp AI", "Medical AI", "Legal Assistant"
BRAND_LOGO_URL=https://your-domain.com/logo.png
BRAND_FAVICON_URL=https://your-domain.com/favicon.ico

# ─── Theme Colors ───────────────────────────────────────
THEME_PRIMARY_COLOR=#7C3AED            # Main color (purple by default)
THEME_ACCENT_COLOR=#06B6D4             # Accent color (cyan by default)
THEME_TEXT_COLOR=#1F2937               # Text color (dark gray)
THEME_BACKGROUND_COLOR=#FFFFFF         # Background (white)
THEME_SUCCESS_COLOR=#10B981            # Success (green)
THEME_ERROR_COLOR=#EF4444              # Error (red)
THEME_WARNING_COLOR=#F59E0B            # Warning (amber)

# ─── Company Info ────────────────────────────────────────
COMPANY_NAME=Your Company Inc.
COMPANY_WEBSITE=https://yourcompany.com
COMPANY_SUPPORT_EMAIL=support@yourcompany.com
COMPANY_LOGO_LIGHT=https://your-domain.com/logo-light.png
COMPANY_LOGO_DARK=https://your-domain.com/logo-dark.png

# ─── ChatBot Personality ────────────────────────────────
CHATBOT_NAME=YourAI Assistant           # e.g., "MediBot", "LegalAssist", "InsuranceAI"
CHATBOT_GREETING=Hello! I'm YourAI Assistant. How can I help?
CHATBOT_PLACEHOLDER=Ask me anything...

# ─── Industry/Vertical ──────────────────────────────────
INDUSTRY_TYPE=general                   # Options: general, healthcare, legal, finance, education, ecommerce, saas
```

---

## Industry-Specific Presets

Choose one and copy the colors into `.env`:

### 🏥 Healthcare

```bash
BRAND_NAME=MediBot AI
CHATBOT_NAME=Medical Assistant
THEME_PRIMARY_COLOR=#0066CC            # Medical blue
THEME_ACCENT_COLOR=#00AA44             # Health green
INDUSTRY_TYPE=healthcare
```

### ⚖️ Legal

```bash
BRAND_NAME=LegalAssist AI
CHATBOT_NAME=Legal Advisor
THEME_PRIMARY_COLOR=#1a1a2e            # Dark blue
THEME_ACCENT_COLOR=#16213e             # Navy
INDUSTRY_TYPE=legal
```

### 💼 Finance/Banking

```bash
BRAND_NAME=FinanceAI Pro
CHATBOT_NAME=Financial Advisor
THEME_PRIMARY_COLOR=#003366            # Banking blue
THEME_ACCENT_COLOR=#FFB81C             # Gold
INDUSTRY_TYPE=finance
```

### 📚 Education

```bash
BRAND_NAME=EduAI Tutor
CHATBOT_NAME=Tutor Assistant
THEME_PRIMARY_COLOR=#6200EA            # Deep purple
THEME_ACCENT_COLOR=#03DAC6             # Teal
INDUSTRY_TYPE=education
```

### 🛒 E-Commerce

```bash
BRAND_NAME=ShopAI Assistant
CHATBOT_NAME=Shopping Helper
THEME_PRIMARY_COLOR=#FF6B6B            # Vibrant red
THEME_ACCENT_COLOR=#4ECDC4             # Turquoise
INDUSTRY_TYPE=ecommerce
```

### 💻 SaaS/Tech

```bash
BRAND_NAME=TechAI Pro
CHATBOT_NAME=Tech Support Bot
THEME_PRIMARY_COLOR=#0047AB            # Bright blue
THEME_ACCENT_COLOR=#00D9FF             # Cyan
INDUSTRY_TYPE=saas
```

### 🎨 Creative/Design

```bash
BRAND_NAME=CreativeAI Studio
CHATBOT_NAME=Design Consultant
THEME_PRIMARY_COLOR=#FF1493            # Deep pink
THEME_ACCENT_COLOR=#FFD700             # Gold
INDUSTRY_TYPE=creative
```

---

## Custom Branding Elements

### Update Admin Dashboard Title

Edit `backend/app/main.py`:

```python
app = FastAPI(
    title="Your Company Name — AI Assistant API",
    description="Your custom description here",
    version="1.0.0",
    lifespan=lifespan
)
```

### Update Chat Widget

The widget will automatically use colors from `.env`. Just rebuild:

```bash
docker compose build frontend
docker compose up -d frontend
```

### Custom Email Templates

Create `backend/templates/emails/`:

```bash
mkdir -p backend/templates/emails
```

Create `welcome_email.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; }
        .header { background: {{ THEME_PRIMARY_COLOR }}; padding: 20px; color: white; }
        .logo { max-width: 200px; }
    </style>
</head>
<body>
    <div class="header">
        <img src="{{ COMPANY_LOGO_URL }}" class="logo" alt="{{ BRAND_NAME }}">
        <h1>Welcome to {{ BRAND_NAME }}</h1>
    </div>
    <div class="content">
        <p>Hi {{ user_name }},</p>
        <p>Welcome to {{ BRAND_NAME }}! Your account is ready.</p>
        <p>Get started: <a href="{{ PLATFORM_URL }}">Login to Dashboard</a></p>
    </div>
    <div class="footer">
        <p>© {{ CURRENT_YEAR }} {{ COMPANY_NAME }}. All rights reserved.</p>
        <p><a href="{{ COMPANY_WEBSITE }}">Website</a> | <a href="mailto:{{ COMPANY_SUPPORT_EMAIL }}">Support</a></p>
    </div>
</body>
</html>
```

---

## Logo & Assets

1. **Create a logos folder:**
   ```bash
   mkdir -p public/assets/logos
   ```

2. **Add your logos:**
   - `public/assets/logos/logo.png` (main logo)
   - `public/assets/logos/logo-dark.png` (for light backgrounds)
   - `public/assets/logos/logo-light.png` (for dark backgrounds)
   - `public/assets/logos/favicon.ico` (browser tab icon)

3. **Update `.env`:**
   ```bash
   BRAND_LOGO_URL=/assets/logos/logo.png
   BRAND_FAVICON_URL=/assets/logos/favicon.ico
   ```

---

## Complete Example: Tech Company

```bash
# .env branding section
BRAND_NAME=TechVision AI
CHATBOT_NAME=TechBot Pro
CHATBOT_GREETING=Welcome to TechVision AI! Ready to transform your business?
CHATBOT_PLACEHOLDER=Ask about our AI solutions...

THEME_PRIMARY_COLOR=#0047AB            # Blue
THEME_ACCENT_COLOR=#00D9FF             # Cyan
THEME_TEXT_COLOR=#1F2937
THEME_BACKGROUND_COLOR=#FFFFFF

COMPANY_NAME=TechVision Inc.
COMPANY_WEBSITE=https://techvision.com
COMPANY_SUPPORT_EMAIL=support@techvision.com

INDUSTRY_TYPE=saas

# Admin settings
ADMIN_DASHBOARD_TITLE=TechVision AI Control Panel
```

---

## Apply Branding

After editing `.env`:

```bash
# Rebuild frontend with new colors
docker compose build frontend

# Restart services
docker compose up -d

# Access
http://your-server/
```

The branding will be applied to:
- ✅ Admin dashboard
- ✅ Chat widget
- ✅ API documentation
- ✅ Email templates
- ✅ Login page
- ✅ All UI elements

---

## Advanced: Custom CSS

Create `backend/static/custom-theme.css`:

```css
:root {
  --primary-color: var(--theme-primary-color);
  --accent-color: var(--theme-accent-color);
  --text-color: var(--theme-text-color);
  --background-color: var(--theme-background-color);
}

/* Your custom styles */
.navbar {
  background: var(--primary-color);
  color: white;
}

.chat-bubble {
  background: var(--accent-color);
  border-radius: 12px;
}
```

Reference in HTML:
```html
<link rel="stylesheet" href="/custom-theme.css">
```

---

## White Label Option

For complete white-labeling (remove RAZE branding):

```bash
# .env
BRAND_NAME=Your Brand Name
HIDE_RAZE_BRANDING=true
SHOW_COMPANY_FOOTER=true
CUSTOM_DOMAIN=yourbrand.com
```

Then:
- Admin dashboard shows only your brand
- Chat widget is fully customized
- No "Powered by RAZE" attribution
- Company logo in top-left
- Custom colors throughout

---

## Quick Color Reference

| Industry | Primary | Accent | Hex Codes |
|----------|---------|--------|-----------|
| Healthcare | Medical Blue | Health Green | #0066CC, #00AA44 |
| Legal | Navy | Dark Blue | #1a1a2e, #16213e |
| Finance | Banking Blue | Gold | #003366, #FFB81C |
| Education | Purple | Teal | #6200EA, #03DAC6 |
| E-Commerce | Red | Turquoise | #FF6B6B, #4ECDC4 |
| Tech | Bright Blue | Cyan | #0047AB, #00D9FF |
| Creative | Pink | Gold | #FF1493, #FFD700 |

---

## Branding Checklist

- [ ] Edit `.env` with company name & colors
- [ ] Add logo files to `public/assets/logos/`
- [ ] Update email templates (if using)
- [ ] Rebuild frontend: `docker compose build frontend`
- [ ] Restart services: `docker compose up -d`
- [ ] Verify admin dashboard shows correct branding
- [ ] Verify chat widget uses correct colors
- [ ] Test on mobile (responsive design)
- [ ] Set favicon in browser
- [ ] Test all admin sections

---

## Testing Your Brand

```bash
# Verify colors are applied
curl http://localhost/api/v1/config/theme | jq .

# Check admin dashboard
http://localhost/

# Check chat widget
Look for your colors in browser dev tools
```

---

Done! Your RAZE instance now has custom branding for your industry.

**Next:** Follow DEPLOY_UNIFIED.md to deploy your branded platform.

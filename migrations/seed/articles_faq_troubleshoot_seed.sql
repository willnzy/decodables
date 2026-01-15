-- ============================================================================
-- FAQ & TROUBLESHOOTING ARTICLES SEED FILE
-- ============================================================================
-- Contains: 6 FAQ articles + 8 Troubleshooting articles
-- Split from: articles_seed.sql
-- Template variables: Uses {{variable}} syntax resolved at runtime
-- ============================================================================


-- ============================================================================
-- FAQ ARTICLES (category = 'faq')
-- ============================================================================
-- FAQ articles are grouped by tag for display in the Manual page
-- Each article represents a FAQ category with multiple Q&A pairs in content

-- FAQ: Getting Started
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'faq-getting-started',
    'Getting Started',
    'Common questions about starting with Make Decodables',
    '## What is Make Decodables?

Make Decodables is an AI-powered platform for creating 8-page foldable mini-books (zines). Perfect for educators, parents, and storytellers who want to create printable reading materials quickly.

## How do I create my first project?

Log in to your Dashboard, click "New Project", then use the editor to design pages or click "AI Generate" for automatic creation. Export as PDF when done!

## Do I need design skills?

No! Our AI can generate complete pages for you. Just describe what you want, and the AI creates illustrations. You can also use our templates and sticker library.',
    'faq',
    '["getting-started", "basics", "beginner"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    10,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- FAQ: Credits & Pricing
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'faq-credits-pricing',
    'Credits & Pricing',
    'Questions about pricing plans and credit system',
    '## How much does it cost?

Free: $0 ({{tiers.t1.signupBonus}} credits included). Starter: ${{tiers.t2.monthlyPrice}}/month ({{tiers.t2.monthlyCredits}} monthly credits). Pro: ${{tiers.t3.monthlyPrice}}/month ({{tiers.t3.monthlyCredits}} monthly credits). PDF export is always free!

## What are credits used for?

AI Image Generation costs {{creditCosts.ai_image}} credits per image. OCR/Smart Scan costs {{creditCosts.ocr}} credits per scan. Your first AI image is free! PDF export, saving, and printing are always free.

## Do unused monthly credits roll over?

No, monthly credits reset each billing cycle. However, permanent credits (purchased or earned from sales) never expire.

## How do I get more credits?

Buy Credit Booster (${{pricing.credits_100.price}} = {{pricing.credits_100.amount}} credits, Pro gets {{pricing.pro_discount_percent}}% off), upgrade your plan, or earn credits by selling on the Marketplace (you keep {{marketplace.seller_share_percent}}% of each sale).',
    'faq',
    '["credits", "pricing", "billing", "subscription"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    20,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- FAQ: Features & Plans
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'faq-features-plans',
    'Features & Plans',
    'Questions about plan features and capabilities',
    '## What''s the difference between plans?

Free: {{tiers.t1.maxProjects}} project, basic features. Starter (${{tiers.t2.monthlyPrice}}/mo): {{tiers.t2.maxProjects}} projects, full sticker library, marketplace access. Pro (${{tiers.t3.monthlyPrice}}/mo): {{tiers.t3.maxProjects}} projects, ZIP export, OCR, high-quality AI, commercial license.

## What is the {{trial.duration_days}}-day Free trial?

New Free users can experience Pro features for {{trial.duration_days}} days. After the trial, projects become read-only until you upgrade.

## Can I use my creations commercially?

Pro users have a commercial license. Free and Starter users should use creations for personal/educational purposes only.',
    'faq',
    '["features", "plans", "trial", "commercial"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    30,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- FAQ: Export & Printing
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'faq-export-printing',
    'Export & Printing',
    'Questions about exporting and printing your books',
    '## How do I export my book?

Click "Export" in the editor, then choose "Download PDF" (free for all users) or "Download ZIP" (Pro only). Select Letter or A4 paper size in settings.

## What paper should I use for printing?

For practice: regular copy paper. For final copies: cardstock (65-80 lb) for durability. Print at "Actual Size" or "100%" - don''t use "Fit to Page".

## How do I fold the mini-book?

Check our "Folding Instructions" guide for step-by-step directions. You''ll need scissors to make one cut, then fold into an 8-page book.',
    'faq',
    '["export", "pdf", "print", "folding"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    40,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- FAQ: Marketplace
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'faq-marketplace',
    'Marketplace',
    'Questions about buying and selling on the Marketplace',
    '## How do I buy templates?

Browse the Marketplace, click a listing, and click "Purchase". Credits are deducted instantly. Starter can buy assets only; Pro can buy everything.

## How do I sell my work?

Click "Publish" on your project, fill in details, and submit for review ({{marketplace.review_hours}} hours). Free users cannot publish. Starter can publish free assets only. Pro can publish anything at 0-{{marketplace.max_listing_price}} credits.

## How much do I earn from sales?

You keep {{marketplace.seller_share_percent}}% of each sale as permanent credits. The platform takes a {{marketplace.platform_fee_percent}}% fee. Earnings cannot be withdrawn as cash but can be used for all platform features.',
    'faq',
    '["marketplace", "selling", "buying", "earnings"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    50,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- FAQ: Account & Support
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'faq-account-support',
    'Account & Support',
    'Questions about account management and getting help',
    '## How do I cancel my subscription?

Go to Settings > Subscription > "Manage Subscription" to open the Stripe billing portal. Your access continues until the current billing period ends.

## Is my data secure?

Yes! We use Supabase with row-level security, and Stripe for payments. We never store your full credit card number.

## How do I contact support?

Email: {{site.email}} or WhatsApp: {{site.whatsapp}}. We typically respond within {{support.response_hours}} hours. Pro users get priority support.',
    'faq',
    '["account", "support", "security", "contact"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    60,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);


-- ============================================================================
-- TROUBLESHOOTING ARTICLES (category = 'troubleshooting')
-- ============================================================================
-- Each troubleshooting article represents a common error with its solution

-- Troubleshooting: Insufficient credits
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'troubleshooting-insufficient-credits',
    'Insufficient credits',
    'Your credit balance is too low for this action',
    '## Error Message

"Insufficient credits"

## Problem

You don''t have enough credits to complete the AI generation, OCR scan, or marketplace purchase.

## Solution

Your credit balance is too low. Click "Buy Credits" in the popup, or upgrade to Starter/Pro for monthly credits. Pro users get {{pricing.pro_discount_percent}}% discount on credit purchases.

## Tips

- Check your current balance in the top-right corner of the dashboard
- AI image generation costs {{creditCosts.ai_image}} credits per image
- OCR/Smart Scan costs {{creditCosts.ocr}} credits per scan
- Consider upgrading to a paid plan for monthly credit allowance',
    'troubleshooting',
    '["credits", "error", "payment"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    10,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Troubleshooting: Trial period expired
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'troubleshooting-trial-expired',
    'Trial period expired',
    'Your {{trial.duration_days}}-day Free trial has ended',
    '## Error Message

"Trial period expired"

## Problem

Your {{trial.duration_days}}-day Free trial has ended and your projects are now in read-only mode.

## Solution

Your {{trial.duration_days}}-day Free trial has ended. Projects are now read-only. Upgrade to Starter (${{tiers.t2.monthlyPrice}}/mo) or Pro (${{tiers.t3.monthlyPrice}}/mo) to continue editing.

## What you can still do

- View your existing projects
- Export projects as PDF (always free)
- Browse the Marketplace

## What requires upgrade

- Edit existing projects
- Create new projects
- Use AI image generation
- Access advanced features',
    'troubleshooting',
    '["trial", "expired", "upgrade", "subscription"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    20,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Troubleshooting: Project limit reached
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'troubleshooting-project-limit',
    'Project limit reached',
    'You''ve hit the maximum projects for your tier',
    '## Error Message

"Project limit reached"

## Problem

You''ve created the maximum number of projects allowed for your subscription tier.

## Solution

You''ve hit the maximum projects for your tier (Free: {{tiers.t1.maxProjects}}, Starter: {{tiers.t2.maxProjects}}, Pro: {{tiers.t3.maxProjects}}). Delete unused projects or upgrade to a higher tier.

## Project Limits by Tier

| Tier | Max Projects |
|------|--------------|
| Free | {{tiers.t1.maxProjects}} |
| Starter | {{tiers.t2.maxProjects}} |
| Pro | {{tiers.t3.maxProjects}} |

## How to free up space

1. Go to your Dashboard
2. Find projects you no longer need
3. Click the menu (⋮) and select "Delete"
4. Confirm deletion',
    'troubleshooting',
    '["projects", "limit", "tier", "upgrade"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    30,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Troubleshooting: Content policy violation
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'troubleshooting-content-policy',
    'Content policy violation',
    'Your AI prompt contains restricted content',
    '## Error Message

"Content policy violation"

## Problem

Your AI generation prompt contains content that violates our content policy.

## Solution

Your AI prompt contains restricted content. Avoid violence, adult content, real people''s names, or copyrighted characters. Our AI is designed for children''s content.

## What to avoid

- Violence or weapons
- Adult or inappropriate content
- Real celebrities or public figures
- Copyrighted characters (Disney, Marvel, etc.)
- Scary or disturbing imagery

## Tips for better prompts

- Focus on educational, fun, child-friendly content
- Describe scenes with positive themes
- Use generic characters instead of branded ones
- Be specific but keep it age-appropriate',
    'troubleshooting',
    '["ai", "content", "policy", "moderation"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    40,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Troubleshooting: Failed to save project
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'troubleshooting-save-failed',
    'Failed to save project',
    'Unable to save your project changes',
    '## Error Message

"Failed to save project"

## Problem

Your project changes could not be saved to our servers.

## Solution

Check your internet connection and try again. Your edits are cached locally, so refreshing the page will restore them. Click "Save" to retry.

## Steps to fix

1. Check your internet connection
2. Wait a few seconds and click "Save" again
3. If the problem persists, try refreshing the page
4. Your recent edits are stored locally and should be restored

## If nothing works

- Export your work as PDF to avoid losing it
- Try signing out and signing back in
- Contact support if the issue continues',
    'troubleshooting',
    '["save", "error", "connection", "sync"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    50,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Troubleshooting: Upload failed
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'troubleshooting-upload-failed',
    'Upload failed',
    'Unable to upload your image or file',
    '## Error Message

"Upload failed"

## Problem

Your file upload was rejected or failed to complete.

## Solution

Check file size (max {{limits.upload_max_size_mb}}MB) and format (JPG, PNG, WEBP, GIF, PDF). Compress large images using tools like TinyPNG before uploading.

## Supported formats

- Images: {{limits.supported_image_formats}}
- Documents: PDF

## File size limits

- Maximum file size: {{limits.upload_max_size_mb}}MB
- Recommended: Under 2MB for faster uploads

## How to reduce file size

1. Use [TinyPNG](https://tinypng.com) to compress images
2. Resize large images to smaller dimensions
3. Convert to a more efficient format (like WEBP)',
    'troubleshooting',
    '["upload", "file", "image", "size"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    60,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Troubleshooting: Checkout failed
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'troubleshooting-checkout-failed',
    'Checkout failed',
    'Unable to complete your purchase',
    '## Error Message

"Checkout failed"

## Problem

Your payment or subscription purchase could not be completed.

## Solution

Check your card has sufficient funds. Disable popup blockers (Stripe opens in a new window). Try a different payment method or browser.

## Common causes

1. **Insufficient funds** - Check your card balance
2. **Popup blocked** - The payment window may have been blocked
3. **Card declined** - Your bank may have blocked the transaction
4. **Browser issue** - Try a different browser

## Steps to fix

1. Disable popup blockers for makedecodables.com
2. Try a different payment card
3. Use a different browser (Chrome recommended)
4. Contact your bank if the card is being declined
5. Contact support if the issue persists',
    'troubleshooting',
    '["payment", "checkout", "stripe", "card"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    70,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Troubleshooting: ZIP export requires Pro
INSERT INTO articles (
    slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count, created_at, updated_at
) VALUES (
    'troubleshooting-zip-requires-pro',
    'ZIP export requires Pro',
    'ZIP export is a Pro-only feature',
    '## Error Message

"ZIP export requires Pro"

## Problem

You''re trying to export your project as a ZIP file, but this feature requires a Pro subscription.

## Solution

ZIP export is a Pro-only feature. Upgrade to Pro (${{tiers.t3.monthlyPrice}}/mo), or use the free PDF export available to all users.

## What''s included in ZIP export

- Individual page images (high resolution)
- Print-ready files
- Source files for editing
- Batch export of multiple projects

## Alternative: PDF Export

All users can export as PDF for free! PDF export includes:
- All 8 pages formatted for printing
- Ready to fold instructions
- Optimized for home printing',
    'troubleshooting',
    '["zip", "export", "pro", "upgrade"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    80,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

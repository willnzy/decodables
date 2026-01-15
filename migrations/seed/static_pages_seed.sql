-- ============================================================================
-- STATIC PAGES SEED FILE
-- ============================================================================
-- Contains: Static pages for legal, company, and guide sections
--
-- Page Types:
--   - legal: Privacy Policy, Terms of Service, Billing Policy
--   - company: About Us, Contact Us
--   - guide: Marketplace Guidelines
--
-- Template Variables:
--   Uses {{variable.path}} syntax resolved at runtime by TemplateContext
--   See: decodables-fe/components/static-pages/types.ts
--
-- ============================================================================


-- ============================================================================
-- LEGAL PAGES (page_type = 'legal')
-- ============================================================================

-- Privacy Policy
INSERT INTO static_pages (
    slug, title, subtitle, content, page_type, icon, hero_gradient,
    meta_title, meta_description, is_published, published_at, last_updated_display, sort_order
) VALUES (
    'privacy-policy',
    'Privacy Policy',
    'How we collect, use, and protect your information',
    E'# Privacy Policy

**Last Updated:** {{site.privacy_updated}}

At **{{site.name}}**, we are committed to protecting your privacy and ensuring the security of your personal information. This Privacy Policy explains how we collect, use, disclose, and safeguard your data when you use our platform.

## 1. Information We Collect

### 1.1 Information You Provide

When you create an account or use our services, we may collect:

- **Account Information:** Name, email address, and password (managed securely through Clerk)
- **Profile Information:** Optional profile picture and display name
- **Payment Information:** Billing details processed securely through Stripe (we never store your full credit card number)
- **Content:** Projects, images, and other content you create on our platform
- **Communications:** Messages you send to our support team

### 1.2 Information Collected Automatically

When you use {{site.name}}, we automatically collect:

- **Usage Data:** Pages visited, features used, and interactions with the platform
- **Device Information:** Browser type, operating system, and device identifiers
- **Log Data:** IP address, access times, and referring URLs
- **Cookies:** Session and preference cookies (see Section 6)

### 1.3 Information from Third Parties

We may receive information from:

- **Authentication Providers:** When you sign in with Google or other OAuth providers
- **Payment Processors:** Transaction confirmations from Stripe
- **Analytics Services:** Aggregated usage statistics

## 2. How We Use Your Information

We use collected information to:

### 2.1 Provide and Improve Services

- Operate and maintain the {{site.name}} platform
- Process transactions and send related information
- Respond to your comments, questions, and requests
- Send technical notices, updates, and support messages

### 2.2 Personalization and Analytics

- Personalize your experience based on preferences
- Analyze usage patterns to improve our services
- Develop new features and functionality
- Monitor and prevent fraudulent activity

### 2.3 Communications

- Send promotional communications (with your consent)
- Notify you about changes to our services
- Provide customer support

## 3. Information Sharing

We do **not** sell your personal information. We may share data with:

### 3.1 Service Providers

- **Supabase:** Database hosting with row-level security
- **Clerk:** Authentication and user management
- **Stripe:** Payment processing
- **Vercel/Railway:** Application hosting
- **FAL.ai/OpenAI:** AI image generation (prompts only, not personal data)

### 3.2 Legal Requirements

We may disclose information if required by law, legal process, or government request.

### 3.3 Business Transfers

In the event of a merger, acquisition, or sale of assets, your information may be transferred to the new entity.

## 4. Data Security

We implement industry-standard security measures:

- **Encryption:** All data transmitted via HTTPS/TLS
- **Database Security:** Row-level security policies in Supabase
- **Authentication:** Secure token-based authentication via Clerk
- **Payment Security:** PCI-compliant payment processing via Stripe
- **Access Controls:** Limited employee access to user data

## 5. Data Retention

We retain your data for as long as your account is active or as needed to provide services. You may request deletion of your account and associated data at any time.

### Retention Periods

| Data Type | Retention Period |
|-----------|------------------|
| Account Information | Until account deletion |
| Projects & Content | Until deletion or 30 days after account deletion |
| Payment Records | 7 years (legal requirement) |
| Usage Logs | 90 days |

## 6. Cookies and Tracking

### 6.1 Types of Cookies We Use

- **Essential Cookies:** Required for authentication and security
- **Preference Cookies:** Remember your settings and choices
- **Analytics Cookies:** Help us understand usage patterns

### 6.2 Managing Cookies

You can control cookies through your browser settings. Note that disabling essential cookies may affect platform functionality.

## 7. Your Rights

Depending on your location, you may have the right to:

- **Access:** Request a copy of your personal data
- **Correction:** Update inaccurate information
- **Deletion:** Request deletion of your account and data
- **Portability:** Export your data in a machine-readable format
- **Opt-out:** Unsubscribe from marketing communications

To exercise these rights, contact us at {{site.email}}.

## 8. Children''s Privacy

{{site.name}} is designed for users of all ages, including educational use with children. However:

- Users under 13 should have parental consent
- We do not knowingly collect personal information from children without parental consent
- Parents can contact us to review or delete their child''s information

## 9. International Data Transfers

Your data may be processed in countries other than your own. We ensure appropriate safeguards are in place for international transfers.

## 10. Changes to This Policy

We may update this Privacy Policy periodically. We will notify you of significant changes via email or platform notification. Continued use after changes constitutes acceptance.

## 11. Contact Us

If you have questions about this Privacy Policy:

- **Email:** {{site.email}}
- **WhatsApp:** {{site.whatsapp}}

---

*This Privacy Policy is effective as of the Last Updated date above.*',
    'legal',
    'Shield',
    'from-blue-600 to-indigo-600',
    'Privacy Policy | {{site.name}}',
    'Learn how {{site.name}} collects, uses, and protects your personal information. Your privacy matters to us.',
    true,
    CURRENT_TIMESTAMP,
    'January 2026',
    10
);

-- Terms of Service
INSERT INTO static_pages (
    slug, title, subtitle, content, page_type, icon, hero_gradient,
    meta_title, meta_description, is_published, published_at, last_updated_display, sort_order
) VALUES (
    'terms-of-service',
    'Terms of Service',
    'Please read these terms carefully before using our platform',
    E'# Terms of Service

**Last Updated:** {{site.terms_updated}}

Welcome to **{{site.name}}**! These Terms of Service ("Terms") govern your use of our platform and services. By accessing or using {{site.name}}, you agree to be bound by these Terms.

## 1. Acceptance of Terms

By creating an account or using {{site.name}}, you acknowledge that you have read, understood, and agree to be bound by these Terms and our Privacy Policy. If you do not agree, please do not use our services.

## 2. Description of Service

{{site.name}} is an AI-powered platform for creating 8-page foldable mini-books (zines). Our services include:

- Project creation and editing tools
- AI image generation
- OCR/Smart Scan functionality
- PDF and ZIP export
- Community marketplace
- Template and sticker libraries

## 3. User Accounts

### 3.1 Registration

To use {{site.name}}, you must:

- Provide accurate and complete registration information
- Be at least 13 years old (or have parental consent)
- Maintain the security of your account credentials
- Notify us immediately of any unauthorized access

### 3.2 Account Responsibility

You are responsible for all activities that occur under your account. We reserve the right to suspend or terminate accounts that violate these Terms.

## 4. Subscription Plans and Pricing

### 4.1 Available Plans

| Plan | Price | Features |
|------|-------|----------|
| Free | $0 | {{tiers.t1.maxProjects}} project, {{tiers.t1.signupBonus}} bonus credits |
| {{tiers.t2.displayName}} | ${{tiers.t2.monthlyPrice}}/month | {{tiers.t2.maxProjects}} projects, {{tiers.t2.monthlyCredits}} monthly credits |
| {{tiers.t3.displayName}} | ${{tiers.t3.monthlyPrice}}/month | {{tiers.t3.maxProjects}} projects, {{tiers.t3.monthlyCredits}} monthly credits, commercial license |

### 4.2 Credits System

- AI Image Generation: {{creditCosts.ai_image}} credits per image
- OCR/Smart Scan: {{creditCosts.ocr}} credits per scan
- Monthly credits reset each billing cycle and do not roll over
- Purchased credits are permanent and never expire

### 4.3 Billing

- Subscriptions are billed monthly in advance
- Payments are processed securely through Stripe
- You may cancel your subscription at any time
- Refunds are handled according to our Billing Policy

## 5. Acceptable Use

### 5.1 You Agree To:

- Use {{site.name}} only for lawful purposes
- Respect the intellectual property rights of others
- Not upload harmful, offensive, or illegal content
- Not attempt to circumvent security measures
- Not use automated systems to access the service without permission

### 5.2 Content Guidelines

All content must be appropriate for educational and family use. Prohibited content includes:

- Violence, weapons, or harmful activities
- Adult or sexually explicit material
- Hate speech or discrimination
- Copyrighted material without authorization
- Personal information of others without consent

### 5.3 AI Content Policy

When using AI features, you must:

- Not attempt to generate prohibited content
- Understand that AI-generated content may not be perfect
- Accept responsibility for how you use AI-generated content

## 6. Intellectual Property

### 6.1 Your Content

You retain ownership of content you create. By uploading content, you grant {{site.name}} a license to:

- Store and display your content
- Process content for AI features
- Create backups for data protection

### 6.2 Platform Content

{{site.name}}, including its design, features, and code, is owned by us and protected by intellectual property laws.

### 6.3 Commercial Use

- **Free and {{tiers.t2.displayName}}:** Personal and educational use only
- **{{tiers.t3.displayName}}:** Commercial use permitted with proper attribution

## 7. Marketplace

### 7.1 Selling

- Sellers earn {{marketplace.seller_share_percent}}% of each sale
- Platform fee: {{marketplace.platform_fee_percent}}%
- All items subject to review before listing
- Earnings are in platform credits (not withdrawable as cash)

### 7.2 Buying

- All sales are final
- Credits are non-refundable
- Purchased items are for personal use unless otherwise licensed

## 8. Limitation of Liability

TO THE MAXIMUM EXTENT PERMITTED BY LAW:

- {{site.name}} is provided "AS IS" without warranties
- We are not liable for indirect, incidental, or consequential damages
- Our total liability is limited to the amount you paid us in the past 12 months
- We are not responsible for third-party services (Stripe, AI providers, etc.)

## 9. Indemnification

You agree to indemnify and hold {{site.name}} harmless from any claims, damages, or expenses arising from:

- Your violation of these Terms
- Your content or use of the service
- Your violation of any third-party rights

## 10. Termination

### 10.1 By You

You may terminate your account at any time through account settings. Upon termination:

- Your projects will be deleted after 30 days
- Unused credits will be forfeited
- You may export your content before deletion

### 10.2 By Us

We may suspend or terminate your account if you:

- Violate these Terms
- Engage in fraudulent activity
- Abuse the platform or other users

## 11. Changes to Terms

We may modify these Terms at any time. We will notify you of significant changes via email or platform notification. Continued use after changes constitutes acceptance.

## 12. Governing Law

These Terms are governed by the laws of the State of Delaware, USA, without regard to conflict of law principles.

## 13. Dispute Resolution

Any disputes will be resolved through binding arbitration in accordance with the rules of the American Arbitration Association, except for claims eligible for small claims court.

## 14. Contact Us

For questions about these Terms:

- **Email:** {{site.email}}
- **WhatsApp:** {{site.whatsapp}}

---

*By using {{site.name}}, you acknowledge that you have read and agree to these Terms of Service.*',
    'legal',
    'FileText',
    'from-indigo-600 to-purple-600',
    'Terms of Service | {{site.name}}',
    'Read the Terms of Service for {{site.name}}. Understand your rights and responsibilities when using our platform.',
    true,
    CURRENT_TIMESTAMP,
    'January 2026',
    20
);

-- Billing Policy
INSERT INTO static_pages (
    slug, title, subtitle, content, page_type, icon, hero_gradient,
    meta_title, meta_description, is_published, published_at, last_updated_display, sort_order
) VALUES (
    'billing-policy',
    'Billing Policy',
    'Subscription billing, refunds, and payment information',
    E'# Billing Policy

**Last Updated:** {{site.billing_updated}}

This Billing Policy explains how billing, payments, and refunds work at **{{site.name}}**. Please read this carefully before making any purchases.

## 1. Subscription Plans

### 1.1 Available Plans

| Plan | Monthly Price | Monthly Credits | Max Projects |
|------|---------------|-----------------|--------------|
| Free | $0 | 0 ({{tiers.t1.signupBonus}} bonus on signup) | {{tiers.t1.maxProjects}} |
| {{tiers.t2.displayName}} | ${{tiers.t2.monthlyPrice}} | {{tiers.t2.monthlyCredits}} | {{tiers.t2.maxProjects}} |
| {{tiers.t3.displayName}} | ${{tiers.t3.monthlyPrice}} | {{tiers.t3.monthlyCredits}} | {{tiers.t3.maxProjects}} |

### 1.2 Credit Costs

| Feature | Credits |
|---------|---------|
| AI Image Generation | {{creditCosts.ai_image}} |
| OCR/Smart Scan | {{creditCosts.ocr}} |
| PDF Export | Free |
| Premium Assets | Varies |

## 2. Payment Processing

### 2.1 Payment Methods

We accept payments through **Stripe**, including:

- Credit and debit cards (Visa, Mastercard, American Express)
- Apple Pay and Google Pay (where available)

### 2.2 Currency

All prices are in **US Dollars (USD)**. Currency conversion fees may apply depending on your bank.

### 2.3 Security

- Payments are processed securely through Stripe
- We never store your full credit card number
- All transactions are encrypted with industry-standard security

## 3. Billing Cycle

### 3.1 Subscription Billing

- Subscriptions are billed **monthly** on the date you subscribed
- Payment is charged in advance for each billing period
- Monthly credits are added on each billing date
- Unused monthly credits **do not** roll over to the next month

### 3.2 Credit Purchases

Credit packages are **one-time purchases**:

| Package | Credits | Price |
|---------|---------|-------|
| Small | {{pricing.credits_100.amount}} | ${{pricing.credits_100.price}} |
| Medium | {{pricing.credits_500.amount}} | ${{pricing.credits_500.price}} |
| Large | {{pricing.credits_2000.amount}} | ${{pricing.credits_2000.price}} |

**{{tiers.t3.displayName}} members** receive {{pricing.pro_discount_percent}}% discount on credit purchases.

Purchased credits are **permanent** and never expire.

## 4. Cancellation

### 4.1 How to Cancel

1. Go to **Settings** > **Subscription**
2. Click **Manage Subscription**
3. Select **Cancel Subscription** in the Stripe portal

### 4.2 What Happens After Cancellation

- Your subscription remains active until the end of the current billing period
- After expiration, your account reverts to the Free plan
- You retain access to your projects (within Free plan limits)
- Unused monthly credits are forfeited
- Purchased credits remain available

## 5. Refund Policy

### 5.1 Subscription Refunds

- **Within 7 days of first subscription:** Full refund available
- **After 7 days:** No refunds for partial months
- **Annual subscriptions:** Prorated refund for unused months

### 5.2 Credit Refunds

- **Unused credits:** May be refunded within 14 days of purchase
- **Used credits:** No refunds for credits that have been spent
- **Marketplace purchases:** All sales are final, no refunds

### 5.3 How to Request a Refund

To request a refund:

1. Email {{site.email}} with your account email
2. Include your reason for the refund request
3. We will respond within {{support.response_hours}} hours

### 5.4 Refund Processing

- Refunds are processed to the original payment method
- Processing time: 5-10 business days depending on your bank
- You will receive email confirmation when the refund is processed

## 6. Failed Payments

### 6.1 What Happens

If a payment fails:

1. We will attempt to charge your card again within 3 days
2. You will receive an email notification
3. After 3 failed attempts, your subscription may be suspended

### 6.2 Updating Payment Method

To update your payment method:

1. Go to **Settings** > **Subscription**
2. Click **Manage Subscription**
3. Update your card in the Stripe portal

## 7. Price Changes

### 7.1 Notification

We will provide at least **30 days notice** before any price changes to existing subscribers.

### 7.2 Grandfathering

Existing subscribers may be grandfathered at their current rate at our discretion.

## 8. Taxes

### 8.1 Sales Tax

Applicable sales tax will be added to your purchase based on your location.

### 8.2 Tax Receipts

Tax receipts are available in your Stripe billing portal.

## 9. Enterprise and Education

For enterprise pricing or educational institution discounts, please contact us at {{site.email}}.

## 10. Contact Us

For billing questions or issues:

- **Email:** {{site.email}}
- **WhatsApp:** {{site.whatsapp}}
- **Response time:** Within {{support.response_hours}} hours

---

*This Billing Policy is effective as of the Last Updated date above.*',
    'legal',
    'CreditCard',
    'from-green-600 to-emerald-600',
    'Billing Policy | {{site.name}}',
    'Understand billing, subscriptions, credits, and refunds at {{site.name}}. Clear pricing and payment information.',
    true,
    CURRENT_TIMESTAMP,
    'January 2026',
    30
);


-- ============================================================================
-- COMPANY PAGES (page_type = 'company')
-- ============================================================================

-- About Us
INSERT INTO static_pages (
    slug, title, subtitle, content, page_type, icon, hero_gradient,
    meta_title, meta_description, extra_data, is_published, published_at, last_updated_display, sort_order
) VALUES (
    'about-us',
    'About Us',
    'Empowering educators and storytellers to create beautiful mini-books',
    E'# About {{site.name}}

## Our Mission

We believe every educator, parent, and storyteller should have the tools to create beautiful, engaging reading materials—without needing design skills or expensive software.

**{{site.name}}** was built to make that vision a reality.

## What We Do

{{site.name}} is an AI-powered platform for creating **8-page foldable mini-books** (also known as zines). Our tools help you:

- **Create** custom decodable readers and mini-books
- **Design** with AI-generated illustrations
- **Print** ready-to-fold pages on any home printer
- **Share** your creations on our community marketplace

## Who We Serve

### Educators

K-12 teachers use {{site.name}} to create:
- Decodable readers aligned with phonics sequences
- Classroom story books featuring students'' names
- Educational content for any subject

### Parents

Families use {{site.name}} to create:
- Personalized bedtime stories
- Educational activity books
- Memory books and keepsakes

### Storytellers

Writers and artists use {{site.name}} to:
- Self-publish mini-comics and zines
- Create handmade gifts
- Prototype book ideas

## Our Story

{{site.name}} started with a simple observation: teachers spend countless hours searching for or creating reading materials that match their exact curriculum needs.

We built {{site.name}} to solve this problem—combining modern AI technology with the timeless appeal of mini-books that kids love to hold, fold, and read.

## Our Values

### Simplicity First

We believe tools should get out of the way. You should be able to create a mini-book in minutes, not hours.

### AI for Good

Our AI features are designed to be helpful, safe, and appropriate for all ages. We prioritize child-friendly content generation.

### Community Driven

Our marketplace enables creators to share their work and earn from their creativity. The best ideas come from our community.

### Education Focused

We design every feature with educators in mind. From decodable text patterns to classroom batch printing, we understand what teachers need.

## Technology

{{site.name}} is built with modern, secure technology:

- **Frontend:** Next.js + React
- **Backend:** FastAPI + Python
- **Database:** Supabase (PostgreSQL)
- **AI:** FAL.ai + OpenAI
- **Payments:** Stripe
- **Auth:** Clerk

## Contact Us

We love hearing from our users!

- **Email:** {{site.email}}
- **WhatsApp:** {{site.whatsapp}}

Follow us on social media for updates, tips, and inspiration.

---

*Thank you for being part of the {{site.name}} community!*',
    'company',
    'Users',
    'from-violet-600 to-purple-600',
    'About Us | {{site.name}}',
    'Learn about {{site.name}} - our mission to empower educators and storytellers with AI-powered mini-book creation tools.',
    '{}'::jsonb,
    true,
    CURRENT_TIMESTAMP,
    'January 2026',
    10
);

-- Contact Us
INSERT INTO static_pages (
    slug, title, subtitle, content, page_type, icon, hero_gradient,
    meta_title, meta_description, is_published, published_at, last_updated_display, sort_order
) VALUES (
    'contact-us',
    'Contact Us',
    'We''d love to hear from you',
    E'# Contact Us

We''re here to help! Whether you have a question, feedback, or need support, we''d love to hear from you.

## Get in Touch

### Email Support

📧 **{{site.email}}**

Best for:
- Technical support requests
- Account issues
- Billing questions
- Feature suggestions

**Response time:** Within {{support.response_hours}} hours

### WhatsApp

📱 **{{site.whatsapp}}**

Best for:
- Quick questions
- Real-time support
- Urgent issues

**Available:** Monday - Friday, 9 AM - 6 PM (EST)

## Before You Contact Us

### Check Our Resources

Many common questions are answered in our help center:

- **[FAQ](/manual/faq)** - Frequently asked questions
- **[Getting Started](/manual/getting-started)** - New user guide
- **[Troubleshooting](/manual/troubleshooting-guide)** - Common issues and solutions

### For Billing Issues

1. Go to **Settings** > **Subscription**
2. Click **Manage Subscription** to access the Stripe billing portal
3. You can update payment methods, view invoices, and manage your subscription

## What to Include

To help us assist you faster, please include:

1. **Your account email** (or user code from Settings)
2. **Description of the issue** - What happened? What did you expect?
3. **Steps to reproduce** - How can we see the same issue?
4. **Screenshots** - If applicable, attach images showing the problem
5. **Device/Browser** - What device and browser are you using?

## Priority Support

**{{tiers.t3.displayName}} members** receive priority support with faster response times and dedicated assistance.

[Upgrade to {{tiers.t3.displayName}} →](/pricing)

## Business Inquiries

For partnership, press, or enterprise inquiries, please email {{site.email}} with "Business Inquiry" in the subject line.

## Report a Bug

Found a bug? We appreciate you taking the time to report it!

Please include:
- What you were doing when the bug occurred
- The exact error message (if any)
- Screenshots or screen recordings
- Your device and browser information

## Feature Requests

Have an idea for {{site.name}}? We love hearing from our community!

Email us your feature request at {{site.email}} with "Feature Request" in the subject line. We review all suggestions and prioritize based on community demand.

## Stay Connected

Follow us for updates, tips, and inspiration:

- Share your creations with **#MakeDecodables**
- Join our educator community

---

*We typically respond within {{support.response_hours}} hours during business days.*',
    'company',
    'Mail',
    'from-cyan-600 to-blue-600',
    'Contact Us | {{site.name}}',
    'Get in touch with the {{site.name}} team. Email support, WhatsApp, and helpful resources.',
    true,
    CURRENT_TIMESTAMP,
    'January 2026',
    20
);


-- ============================================================================
-- GUIDE PAGES (page_type = 'guide')
-- ============================================================================

-- Marketplace Guidelines
INSERT INTO static_pages (
    slug, title, subtitle, content, page_type, icon, hero_gradient,
    meta_title, meta_description, is_published, published_at, last_updated_display, sort_order
) VALUES (
    'marketplace-guidelines',
    'Marketplace Guidelines',
    'Rules and best practices for buying and selling on our marketplace',
    E'# Marketplace Guidelines

Welcome to the **{{site.name}} Marketplace**! This guide explains how to buy and sell content while maintaining a safe, high-quality community.

## Overview

The Marketplace is where creators can:
- **Sell** templates, stickers, and assets they''ve created
- **Buy** high-quality content from other creators
- **Discover** new ideas and inspiration

## For Sellers

### Who Can Sell?

| Plan | Selling Rights |
|------|----------------|
| Free | ❌ Cannot sell |
| {{tiers.t2.displayName}} | ✅ Free assets only (0 credits) |
| {{tiers.t3.displayName}} | ✅ Full marketplace access (0-{{marketplace.max_listing_price}} credits) |

### How to List an Item

1. Create your template or asset
2. Click **"Publish to Marketplace"**
3. Fill in the listing details:
   - Title (clear and descriptive)
   - Description (explain what''s included)
   - Price (in credits, max {{marketplace.max_listing_price}})
   - Preview images (up to 5)
   - Category and tags
4. Submit for review

### Review Process

All submissions are reviewed within **{{marketplace.review_hours}} hours**. We check for:

- ✅ Original content (not copied from others)
- ✅ Working functionality
- ✅ Appropriate content (family-friendly)
- ✅ Accurate description
- ✅ Quality standards

### Pricing Your Items

- Templates: 10-100 credits (typical)
- Sticker Packs: 5-50 credits (typical)
- Asset Bundles: 20-{{marketplace.max_listing_price}} credits (typical)

**Tip:** Research similar items to price competitively.

### Earnings

- You earn **{{marketplace.seller_share_percent}}%** of each sale
- Platform fee: **{{marketplace.platform_fee_percent}}%**
- Earnings are added to your **permanent credits**
- Credits cannot be withdrawn as cash but can be used for all platform features

### Example Earnings

| Sale Price | Your Earnings | Platform Fee |
|------------|---------------|--------------|
| 10 credits | 9 credits | 1 credit |
| 50 credits | 45 credits | 5 credits |
| 100 credits | 90 credits | 10 credits |

## For Buyers

### Who Can Buy?

| Plan | Buying Rights |
|------|---------------|
| Free | ❌ Cannot buy |
| {{tiers.t2.displayName}} | ✅ Assets only |
| {{tiers.t3.displayName}} | ✅ Everything |

### How to Purchase

1. Browse the Marketplace
2. Click on an item to preview
3. Click **"Purchase"**
4. Credits are deducted instantly
5. Item is added to your library

### After Purchase

- Purchased items appear in your **Asset Library**
- You can use them in any of your projects
- Items are for **personal use** unless you have a {{tiers.t3.displayName}} license

## Content Guidelines

### Allowed Content

- ✅ Original templates and designs
- ✅ Hand-drawn or AI-generated artwork
- ✅ Educational materials
- ✅ Decorative elements and stickers
- ✅ Backgrounds and patterns

### Prohibited Content

- ❌ Copyrighted material (Disney, Marvel, etc.)
- ❌ Trademarked logos or characters
- ❌ Content depicting real people without consent
- ❌ Violent, scary, or inappropriate imagery
- ❌ Adult or sexually explicit content
- ❌ Hate speech or discriminatory content
- ❌ Low-quality or incomplete items
- ❌ Duplicate or spam listings

## Quality Standards

To maintain marketplace quality:

### Templates Must:
- Be fully functional (all pages work)
- Include clear instructions if needed
- Have professional appearance

### Stickers/Assets Must:
- Have transparent backgrounds (where appropriate)
- Be high resolution (minimum 300 DPI)
- Be properly categorized

## Seller Best Practices

### Create Great Listings

1. **Title:** Clear, descriptive, searchable
2. **Description:** Explain what''s included and how to use it
3. **Images:** Show all pages/items, use mockups
4. **Tags:** Use relevant keywords

### Maintain Quality

- Test your items before listing
- Update items based on feedback
- Respond to buyer questions promptly

### Build Your Reputation

- Start with competitive pricing
- Encourage reviews from buyers
- Create consistent, themed collections

## Buyer Best Practices

### Before Buying

- Preview all pages/items carefully
- Read the description thoroughly
- Check the seller''s other items and reviews

### After Buying

- Leave a review to help other buyers
- Report any issues to support
- Provide feedback to sellers

## Violations and Enforcement

### For Sellers

Violations may result in:
- Listing removal
- Temporary suspension
- Permanent ban from marketplace

### For Buyers

Misuse may result in:
- Account suspension
- Loss of purchased items

## Disputes and Support

### For Issues with Purchases

1. Contact the seller first
2. If unresolved, contact support at {{site.email}}
3. Include your purchase details and description of issue

### Refund Policy

- **Marketplace purchases are final**
- Refunds only granted for:
  - Items that don''t work as described
  - Duplicate purchases (technical error)

## Questions?

Contact us at {{site.email}} for marketplace questions or concerns.

---

*These guidelines are effective immediately and may be updated periodically.*',
    'guide',
    'Store',
    'from-orange-600 to-amber-600',
    'Marketplace Guidelines | {{site.name}}',
    'Learn the rules for buying and selling on the {{site.name}} Marketplace. Quality standards, pricing, and best practices.',
    true,
    CURRENT_TIMESTAMP,
    'January 2026',
    10
);


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Count pages by type
-- SELECT page_type, COUNT(*) as count
-- FROM static_pages
-- WHERE is_published = true
-- GROUP BY page_type
-- ORDER BY page_type;

-- Expected results:
-- | page_type | count |
-- |-----------|-------|
-- | company   | 2     |
-- | guide     | 1     |
-- | legal     | 3     |
-- Total: 6 pages

-- List all pages
-- SELECT slug, title, page_type, sort_order
-- FROM static_pages
-- WHERE is_published = true
-- ORDER BY page_type, sort_order;


-- ============================================================================
-- END OF STATIC PAGES SEED DATA
-- ============================================================================

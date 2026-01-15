-- ============================================================================
-- Articles Seed Data
-- ============================================================================
-- Version: 2.0.0
-- Date: 2026-01-16
-- Description: Seed data for Manual, News, FAQ, and Troubleshooting articles
--
-- Categories:
--   - manual: Help documentation, tutorials
--   - news: Announcements, updates, user stories
--   - faq: Frequently asked questions
--   - troubleshooting: Error solutions
--   - changelog: Release notes (future use)
--
-- Template Variables:
--   Articles use {{variable.path}} placeholders for configurable values.
--   These are resolved at runtime by the frontend from TemplateContext.
--
--   Variables used (aligned with TemplateContext):
--     Tiers:
--     - {{tiers.t1/t2/t3.monthlyPrice}}      - Current tier prices
--     - {{tiers.t1/t2/t3.originalPrice}}     - Original tier prices
--     - {{tiers.t1/t2/t3.monthlyCredits}}    - Monthly credit allowance
--     - {{tiers.t1/t2/t3.maxProjects}}       - Project limits per tier
--     - {{tiers.t1.signupBonus}}             - Signup bonus credits (t1 only)
--
--     Credit Costs:
--     - {{creditCosts.ai_image}}             - AI image generation cost
--     - {{creditCosts.ocr}}                  - OCR/Smart Scan cost
--     - {{creditCosts.ai_page}}              - AI page generation cost
--
--     Pricing:
--     - {{pricing.credits_100.amount/price}} - Small package
--     - {{pricing.credits_500.amount/price}} - Medium package
--     - {{pricing.credits_2000.amount/price}}- Large package
--     - {{pricing.pro_discount_percent}}     - Pro discount percentage
--
--     Marketplace:
--     - {{marketplace.seller_share_percent}} - Seller earnings percentage
--     - {{marketplace.platform_fee_percent}} - Platform fee percentage
--     - {{marketplace.max_listing_price}}    - Maximum listing price
--     - {{marketplace.review_hours}}         - Review time (e.g., "24-48")
--
--     Other:
--     - {{trial.duration_days}}              - Trial period days
--     - {{site.email}}                       - Contact/support email
--     - {{site.whatsapp}}                    - WhatsApp contact
--     - {{support.response_hours}}           - Support response time
--     - {{limits.upload_max_size_mb}}        - Max upload file size
--     - {{limits.supported_image_formats}}   - Supported image formats
--
-- Usage:
--   psql -d your_database -f migrations/seed/articles_seed.sql
-- ============================================================================

-- Clear existing articles (optional - comment out in production)
-- DELETE FROM articles WHERE category IN ('manual', 'news');

-- ============================================================================
-- MANUAL ARTICLES (12 articles)
-- ============================================================================

-- 1. Getting Started with Make Decodables
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'getting-started',
    'Getting Started with Make Decodables',
    'Learn the basics of creating your first foldable mini-book in just a few minutes.',
    E'# Getting Started with Make Decodables

Welcome to Make Decodables! This guide will walk you through creating your first foldable mini-book in just a few minutes.

## What is Make Decodables?

Make Decodables is an online tool that helps teachers, parents, and storytellers create beautiful **foldable mini-books** (also known as zines). These 8-page booklets are perfect for:

- **Decodable readers** for phonics instruction
- **Story starters** for creative writing
- **Informational booklets** for any subject
- **Personalized gifts** and keepsakes

## Creating Your First Book

### Step 1: Start a New Project

1. Click the **"Create New Book"** button on your dashboard
2. Choose a template or start from blank
3. Give your project a name

### Step 2: Design Your Pages

Each mini-book has **8 pages**:
- Cover (Page 1)
- Inside pages (Pages 2-7)
- Back cover (Page 8)

Use our editor to:
- Add text with custom fonts
- Insert images from our library or upload your own
- Use AI to generate illustrations
- Add stickers and decorations

### Step 3: Export and Print

When you''re done:
1. Click **"Export PDF"**
2. Print on a single sheet of paper
3. Follow our [folding instructions](/manual/folding-instructions) to create your book!

## Tips for Success

- **Start simple**: Your first book doesn''t need to be perfect
- **Use templates**: They provide a great starting point
- **Preview often**: Check how your book will look when printed
- **Save frequently**: Your work is auto-saved, but manual saves ensure nothing is lost

## Next Steps

- [Using AI to Generate Images](/manual/ai-image-generation)
- [Designing Beautiful Pages](/manual/designing-pages)
- [Tips for Teachers](/manual/classroom-tips)

Happy creating! 🎨',
    'manual',
    '["getting-started", "tutorial", "basics", "beginner"]'::jsonb,
    NULL,
    true,
    true,
    CURRENT_TIMESTAMP,
    10,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 2. Using AI to Generate Images
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'ai-image-generation',
    'Using AI to Generate Images',
    'Master the art of creating stunning illustrations with AI prompts for your books.',
    E'# Using AI to Generate Images

Create beautiful, unique illustrations for your books using our AI image generation feature.

## How It Works

Our AI image generator uses advanced machine learning to create custom illustrations based on your text descriptions (prompts).

**Cost**: {{creditCosts.ai_image}} credits per image generated

## Writing Effective Prompts

The key to great AI images is writing clear, descriptive prompts.

### Basic Structure

A good prompt includes:
1. **Subject**: What you want to see (a cat, a house, a child)
2. **Style**: How it should look (cartoon, watercolor, realistic)
3. **Details**: Colors, mood, setting

### Examples

| Simple Prompt | Better Prompt |
|--------------|---------------|
| A dog | A friendly golden retriever puppy playing in a sunny meadow, cartoon style |
| A house | A cozy cottage with a red roof and flower garden, watercolor illustration |
| A teacher | A smiling teacher reading to children in a colorful classroom, flat design |

## Style Presets

Choose from our pre-configured styles:

- **Cartoon**: Bold lines, bright colors, kid-friendly
- **Watercolor**: Soft, artistic, painterly
- **Realistic**: Photo-like, detailed
- **Flat Design**: Modern, clean, minimal
- **Pixel Art**: Retro, game-style
- **Sketch**: Hand-drawn, pencil-like

## Advanced Features

### Reference Images

Upload a reference image to guide the AI:
1. Click "Add Reference Image"
2. Upload your image
3. The AI will use it as inspiration (not copy it)

### Negative Prompts

Tell the AI what to avoid:
- "no text"
- "no watermarks"
- "no dark colors"

## Best Practices

1. **Be specific**: More details = better results
2. **Iterate**: Generate multiple versions and pick the best
3. **Use style presets**: They''re optimized for book illustrations
4. **Check for errors**: AI can sometimes make mistakes with hands, text, etc.

## Troubleshooting

**Image doesn''t match my prompt?**
- Try being more specific
- Use different wording
- Add a style preset

**Image has artifacts or errors?**
- Regenerate with the same prompt
- Simplify the prompt
- Report persistent issues to support

## Credits Usage

- Each generation: {{creditCosts.ai_image}} credits
- Failed generations: No credits charged
- Monthly subscribers: Credits included in plan

---

Ready to try it? Open a project and click the **AI Image** button!',
    'manual',
    '["ai", "images", "prompts", "generation", "tutorial"]'::jsonb,
    NULL,
    true,
    true,
    CURRENT_TIMESTAMP,
    20,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 3. Designing Beautiful Pages
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'designing-pages',
    'Designing Beautiful Pages',
    'Tips and tricks for creating visually appealing page layouts using our editor.',
    E'# Designing Beautiful Pages

Learn how to create visually stunning pages that engage readers and make your books shine.

## Layout Principles

### The Rule of Thirds

Divide your page into a 3x3 grid. Place important elements along the lines or at intersections for visual balance.

### White Space

Don''t fill every corner! Empty space:
- Improves readability
- Creates visual breathing room
- Highlights important elements

### Visual Hierarchy

Guide the reader''s eye:
1. **Large elements** draw attention first
2. **Color contrast** creates focus
3. **Position** (top-left is read first in English)

## Working with Text

### Font Pairing

Use 2-3 fonts maximum:
- **Headings**: Bold, decorative fonts
- **Body text**: Clean, readable fonts
- **Accents**: Fun fonts for emphasis

### Text Sizing

- **Titles**: 24-36pt
- **Body text**: 12-16pt (larger for young readers)
- **Captions**: 10-12pt

### Readability Tips

- Left-align body text
- Use adequate line spacing (1.2-1.5x)
- Ensure contrast between text and background

## Working with Images

### Image Placement

- **Full-bleed**: Image extends to page edges
- **Framed**: Image with border/margin
- **Floating**: Image with text wrap

### Image Quality

- Use high-resolution images (300 DPI for print)
- Avoid stretching images
- Check how images look when printed

## Color Usage

### Color Schemes

- **Monochromatic**: Shades of one color
- **Complementary**: Opposite colors on the wheel
- **Analogous**: Adjacent colors on the wheel

### For Young Readers

- Use bright, saturated colors
- High contrast for visibility
- Consistent color coding (characters, themes)

## Page Types

### Cover Page

- Large, eye-catching title
- Main illustration
- Author name (optional)

### Text-Heavy Pages

- Balance text with visuals
- Use pull quotes or callouts
- Include illustrations to break up text

### Image-Focused Pages

- Let the image shine
- Minimal text overlay
- Consider full-bleed layouts

## Templates

Start with our templates for:
- Consistent page layouts
- Pre-designed color schemes
- Professional-looking results

---

**Pro Tip**: Preview your book at actual print size before finalizing!',
    'manual',
    '["design", "layout", "tips", "visual", "tutorial"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    30,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 4. Exporting and Printing Your Books
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'exporting-printing',
    'Exporting and Printing Your Books',
    'A complete guide to exporting PDFs and printing your foldable mini-books.',
    E'# Exporting and Printing Your Books

Learn how to export your creations and print perfect foldable mini-books.

## Export Options

### PDF Export

The most common export format:
1. Click **"Export"** in the editor
2. Select **"PDF"**
3. Choose quality settings
4. Download your file

**Quality Settings**:
- **Draft**: Fast, lower quality (for proofing)
- **Standard**: Good balance of quality and file size
- **High**: Best quality (recommended for printing)

### Image Export

Export individual pages as images:
- PNG format (best quality)
- JPG format (smaller file size)

## Printing Guide

### Paper Selection

**Recommended**:
- **Weight**: 24-28 lb (90-105 gsm)
- **Type**: Bright white, matte finish
- **Size**: US Letter or A4

**For durability**: Use cardstock (65-80 lb)

### Printer Settings

1. **Paper size**: Match your export (Letter/A4)
2. **Orientation**: Landscape
3. **Scaling**: 100% (do not fit to page)
4. **Quality**: Best/High
5. **Color**: Color (or grayscale if preferred)

### Print Checklist

- [ ] Preview looks correct
- [ ] Paper loaded correctly
- [ ] Correct side facing up
- [ ] Printer has enough ink/toner

## After Printing

### Folding Your Book

See our detailed [Folding Instructions](/manual/folding-instructions) guide.

Quick overview:
1. Fold paper in half lengthwise
2. Fold in half again
3. Fold once more
4. Cut the center slit
5. Open and refold into book shape

### Finishing Touches

- Crease folds sharply with a bone folder
- Trim edges if needed
- Add a staple for extra durability (optional)

## Troubleshooting

**Colors look different when printed?**
- Calibrate your monitor
- Use printer color management
- Test print on same paper type

**Pages are cut off?**
- Check scaling is set to 100%
- Verify paper size matches export

**Print quality is poor?**
- Increase export quality
- Check printer ink levels
- Clean printer heads

## Batch Printing

For classroom sets:
1. Export high-quality PDF
2. Print multiple copies
3. Consider professional printing for large quantities

---

**Tip**: Always do a test print before printing multiple copies!',
    'manual',
    '["export", "pdf", "print", "printing", "tutorial"]'::jsonb,
    NULL,
    true,
    true,
    CURRENT_TIMESTAMP,
    40,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 5. How to Fold Your Mini-Book
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'folding-instructions',
    'How to Fold Your Mini-Book',
    'Step-by-step folding instructions to transform your printed page into a book.',
    E'# How to Fold Your Mini-Book

Transform a single printed sheet into an 8-page mini-book with these simple steps.

## What You''ll Need

- Your printed page
- Scissors
- A flat surface
- Optional: bone folder or ruler for crisp creases

## Step-by-Step Instructions

### Step 1: First Fold (Lengthwise)

1. Place your printed page face-down
2. Fold in half **lengthwise** (hot dog fold)
3. Crease firmly and unfold

### Step 2: Second Fold (Widthwise)

1. Fold in half **widthwise** (hamburger fold)
2. Crease firmly and unfold

### Step 3: Third Fold (Quarters)

1. Fold both short edges to meet at the center crease
2. Crease firmly

### Step 4: Cut the Center

1. Keep the paper folded from Step 3
2. Find the center fold line
3. Cut along this line **only from the fold to the center point**
4. Do NOT cut all the way through!

### Step 5: Open and Refold

1. Unfold the paper completely
2. You should see a slit in the center
3. Fold lengthwise again (Step 1 fold)
4. Push the ends toward each other
5. The slit will open into a diamond shape

### Step 6: Form the Book

1. Continue pushing until pages form
2. Flatten into book shape
3. The cover should be on front

## Video Tutorial

[Watch our 2-minute folding video]

## Common Mistakes

### Cut too far?
If you cut through the entire fold, tape the ends together and try again.

### Pages in wrong order?
Check that your original print was oriented correctly. The cover should be in the top-right when printing.

### Book won''t stay closed?
- Use a heavier paper stock
- Add a small staple at the spine
- Use a paper clip while reading

## Tips for Perfect Folds

1. **Use a bone folder** or ruler edge for crisp creases
2. **Work on a hard surface** for clean folds
3. **Take your time** - rushing leads to crooked folds
4. **Practice first** with scrap paper

## Teaching Kids to Fold

- Demonstrate each step slowly
- Use larger paper for easier handling
- Pre-crease the folds for younger children
- Make it a fun assembly activity!

---

**Congratulations!** You''ve made your first mini-book! 📚',
    'manual',
    '["folding", "printing", "tutorial", "assembly", "getting-started"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    50,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 6. Using OCR & Smart Scan
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'ocr-smart-scan',
    'Using OCR & Smart Scan',
    'Extract text from images and handwritten notes using our OCR feature.',
    E'# Using OCR & Smart Scan

Convert images of text into editable text with our OCR (Optical Character Recognition) feature.

## What is OCR?

OCR technology reads text from images and converts it to editable digital text. Use it to:

- Digitize handwritten notes
- Extract text from photos
- Convert scanned documents
- Import text from worksheets

**Cost**: {{creditCosts.ocr}} credits per scan

## How to Use Smart Scan

### Step 1: Access the Feature

1. Open your project
2. Click the **"Smart Scan"** button
3. Or drag an image directly to the scan area

### Step 2: Upload Your Image

Supported formats:
- JPG/JPEG
- PNG
- PDF (first page only)

**Image requirements**:
- Clear, readable text
- Good lighting (no harsh shadows)
- Straight alignment (minimal skew)

### Step 3: Review & Edit

After scanning:
1. Review the extracted text
2. Edit any errors
3. Format as needed
4. Insert into your page

## Best Practices

### For Best Results

- **Good lighting**: Even, natural light works best
- **High contrast**: Dark text on light background
- **Clean images**: No wrinkles, stains, or obstructions
- **Straight alignment**: Hold camera level

### Image Quality Tips

| Good | Poor |
|------|------|
| Flat, well-lit document | Crumpled, shadowy image |
| Clear, printed text | Faded or blurry text |
| High resolution | Low resolution |
| Single page | Multiple overlapping pages |

## Supported Languages

Smart Scan works best with:
- English
- Spanish
- French
- German
- Other Latin-alphabet languages

## Troubleshooting

**Text not recognized?**
- Improve image quality
- Ensure text is large enough
- Try a higher resolution image

**Wrong characters?**
- OCR isn''t perfect - always review
- Handwriting may have lower accuracy
- Unusual fonts may cause errors

**Partial recognition?**
- Check image isn''t cropped
- Ensure all text is visible
- Avoid curved or warped text

## Use Cases

### For Teachers

- Digitize student writing samples
- Convert printed worksheets to editable format
- Import text from educational materials

### For Parents

- Preserve children''s handwritten stories
- Create books from handwritten notes
- Digitize letters and cards

---

**Pro Tip**: For handwritten text, print clearly and use dark ink for best results!',
    'manual',
    '["ocr", "scan", "text", "ai", "features"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    60,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 7. Selling on the Marketplace
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'marketplace-guide',
    'Selling on the Marketplace',
    'How to publish your templates and assets to earn credits from other creators.',
    E'# Selling on the Marketplace

Share your creations and earn credits when others purchase your templates and assets.

## What Can You Sell?

### Templates

Complete book layouts that others can customize:
- Story templates
- Educational worksheets
- Activity books
- Themed designs

### Assets

Individual elements for others to use:
- Sticker sets
- Background patterns
- Illustration packs
- Border and frame collections

## Getting Started

### Requirements

To sell on the marketplace:
- Active account (any tier)
- Original content (you created it)
- Meet quality guidelines

### Publishing Your First Item

1. Create your template or asset
2. Click **"Publish to Marketplace"**
3. Set your price (in credits)
4. Add title, description, and tags
5. Upload preview images
6. Submit for review

## Pricing Your Items

### Suggested Pricing

| Type | Credit Range |
|------|--------------|
| Simple template | 10-25 credits |
| Complex template | 25-50 credits |
| Sticker pack (10+) | 15-30 credits |
| Background set | 10-20 credits |
| Premium bundle | 50-100 credits |

### Pricing Tips

- Research similar items
- Consider time invested
- Factor in uniqueness
- Start lower to build reviews

## Earning Credits

When someone purchases your item:
- You earn **{{marketplace.seller_share_percent}}%** of the sale price
- Credits are added to your permanent balance
- Use credits for AI features or to buy other items

### Example

If your template sells for 30 credits:
- You earn: {{marketplace.example_earning_30}} credits
- Platform fee: {{marketplace.example_fee_30}} credits

## Quality Guidelines

### Your items should:

✅ Be original creations
✅ Have clear, accurate previews
✅ Include helpful descriptions
✅ Work correctly when downloaded
✅ Follow community guidelines

### Avoid:

❌ Copyrighted material
❌ Low-quality or rushed work
❌ Misleading descriptions
❌ Inappropriate content

## Marketing Your Items

### Great Listings Include:

1. **Eye-catching preview**: Show your item at its best
2. **Clear title**: Descriptive and searchable
3. **Detailed description**: What''s included, how to use
4. **Relevant tags**: Help buyers find you
5. **Multiple images**: Show different angles/uses

## Tracking Sales

View your seller dashboard for:
- Total earnings
- Sales history
- Popular items
- Buyer feedback

---

Ready to start selling? Create something amazing and share it with the community!',
    'manual',
    '["marketplace", "selling", "credits", "business", "templates"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    70,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 8. Working with Stickers
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'stickers-library',
    'Working with Stickers',
    'Explore our sticker library and learn how to add them to your pages.',
    E'# Working with Stickers

Add fun and personality to your books with our extensive sticker library.

## Accessing Stickers

1. Open your project
2. Click the **"Stickers"** tab in the sidebar
3. Browse categories or search
4. Click to add to your page

## Sticker Categories

### Characters
- People (diverse ages, ethnicities)
- Animals (pets, wildlife, fantasy)
- Fantasy creatures

### Objects
- School supplies
- Food and drinks
- Toys and games
- Nature elements

### Decorations
- Borders and frames
- Stars and shapes
- Speech bubbles
- Arrows and pointers

### Themed Sets
- Holidays
- Seasons
- Educational
- Celebrations

## Using Stickers Effectively

### Sizing

- **Large stickers**: Main illustrations, focal points
- **Medium stickers**: Supporting elements
- **Small stickers**: Decorations, accents

### Placement Tips

1. **Don''t overcrowd**: Less is often more
2. **Create balance**: Distribute evenly
3. **Layer thoughtfully**: Foreground/background
4. **Align with text**: Support, don''t distract

## Editing Stickers

### Available Controls

- **Resize**: Drag corners to scale
- **Rotate**: Use rotation handle
- **Flip**: Horizontal/vertical
- **Layer order**: Send forward/backward

### Maintaining Quality

- Don''t stretch beyond original size
- Keep proportions locked when scaling
- Use vector stickers for best quality

## Creating Custom Stickers

### Upload Your Own

1. Click **"Upload"** in stickers panel
2. Select PNG image (transparent background)
3. Image is saved to your library

### Requirements

- PNG format recommended
- Transparent background
- High resolution (300+ DPI)
- Max file size: 5MB

## Sticker Packs

### Free Stickers

Basic stickers included with all accounts.

### Premium Packs

Available on the marketplace:
- Larger variety
- Higher quality
- Unique designs
- Support creators

## Tips for Different Projects

### Decodable Readers
- Use simple, clear images
- Match text content
- Consistent style throughout

### Story Books
- Expressive characters
- Scene-setting elements
- Action stickers

### Educational Books
- Relevant illustrations
- Diagrams and charts
- Icons and symbols

---

**Have fun decorating your books!** 🎨',
    'manual',
    '["stickers", "assets", "design", "library", "decoration"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    80,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 9. Tips for Teachers: Classroom Use
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'classroom-tips',
    'Tips for Teachers: Classroom Use',
    'Best practices for using Make Decodables in K-12 classroom settings.',
    E'# Tips for Teachers: Classroom Use

Make Decodables is a powerful tool for educators. Here''s how to make the most of it in your classroom.

## Why Mini-Books for Learning?

### Benefits

- **Engagement**: Students love creating their own books
- **Ownership**: Pride in completed projects
- **Differentiation**: Customize for individual needs
- **Multi-modal**: Visual, reading, writing, hands-on

### Research-Backed

Mini-books support:
- Phonics instruction
- Reading fluency
- Writing development
- Content retention

## Classroom Applications

### Literacy Instruction

**Decodable Readers**
- Target specific phonics patterns
- Control vocabulary progression
- Create personalized readers
- Practice fluency with familiar text

**Sight Word Books**
- Focus on high-frequency words
- Repetitive, predictable text
- Student illustrations

### Writing Instruction

**Story Writing**
- Narrative structure practice
- Beginning, middle, end
- Character development
- Dialogue writing

**Informational Writing**
- Research projects
- All-about books
- How-to guides

### Content Areas

**Science**
- Life cycles
- Weather journals
- Animal reports

**Social Studies**
- Community helpers
- Historical figures
- Cultural celebrations

**Math**
- Number books
- Word problems
- Math journals

## Classroom Management

### Whole Class Projects

1. Model the process first
2. Create a class book together
3. Establish clear expectations
4. Set time limits for each step

### Individual Projects

1. Provide templates
2. Allow for creativity
3. Conference during work time
4. Celebrate completed work

### Station/Center Use

- Set up a "Book Making" station
- Rotate students through
- Pre-load templates
- Have materials ready

## Tech Tips

### With Limited Devices

- Rotate device access
- Pre-create templates
- Use projection to demonstrate
- Print and work offline

### 1:1 Environments

- Assign individual logins
- Save work to cloud
- Peer collaboration
- Gallery walks

## Assessment Ideas

### Process Assessment

- Planning/brainstorming
- Draft development
- Revision efforts
- Final product

### Product Assessment

- Content accuracy
- Writing conventions
- Design choices
- Completeness

### Student Self-Assessment

- Reflection journals
- Rubric self-scoring
- Goal setting

## Sharing Student Work

- Author''s chair readings
- Classroom library
- Family take-home
- Digital portfolios
- School displays

## Getting Started Checklist

- [ ] Create teacher account
- [ ] Explore templates
- [ ] Plan first project
- [ ] Test printing/folding
- [ ] Prepare student materials
- [ ] Schedule instruction time

---

**Need more ideas?** Join our educator community for resources and inspiration!',
    'manual',
    '["teachers", "classroom", "education", "k12", "curriculum"]'::jsonb,
    NULL,
    true,
    true,
    CURRENT_TIMESTAMP,
    90,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 10. Understanding Subscriptions & Credits
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'subscription-credits',
    'Understanding Subscriptions & Credits',
    'Everything you need to know about plans, credits, and billing.',
    E'# Understanding Subscriptions & Credits

Learn about our subscription plans and how credits work.

## Subscription Plans

### Free Plan

**Price**: $0/month

- {{tiers.t1.signupBonus}} bonus credits on signup (permanent)
- Basic features
- Community templates
- Standard export quality

### Starter Plan

**Price**: ${{tiers.t2.monthlyPrice}}/month (was ${{tiers.t2.originalPrice}})

- {{tiers.t2.monthlyCredits}} monthly credits
- All Free features plus:
- AI image generation
- PDF export
- Priority support

### Pro Plan

**Price**: ${{tiers.t3.monthlyPrice}}/month (was ${{tiers.t3.originalPrice}})

- {{tiers.t3.monthlyCredits}} monthly credits
- All Starter features plus:
- Commercial license
- Advanced templates
- Bulk export

## Understanding Credits

### What Are Credits?

Credits are the currency for AI features:

| Feature | Cost |
|---------|------|
| AI Image Generation | {{creditCosts.ai_image}} credits |
| Smart Scan (OCR) | {{creditCosts.ocr}} credits |
| AI Page Generation | {{creditCosts.ai_page}} credits |

### Credit Types

**Monthly Credits**
- Included with paid plans
- Reset each billing cycle
- Do not roll over
- Used first

**Permanent Credits**
- From signup bonus or purchases
- Never expire
- Used after monthly credits

### Credit Usage Order

1. Monthly credits (used first)
2. Permanent credits (used second)

## Buying Additional Credits

Need more credits? Purchase permanent credits:

| Package | Credits | Price |
|---------|---------|-------|
| Small | {{pricing.credits_100.amount}} | ${{pricing.credits_100.price}} |
| Medium | {{pricing.credits_500.amount}} | ${{pricing.credits_500.price}} |
| Large | {{pricing.credits_2000.amount}} | ${{pricing.credits_2000.price}} |

Pro members receive {{pricing.pro_discount_percent}}% discount on credit purchases.

## Billing FAQ

### When am I billed?

- Monthly on your signup anniversary date
- Credits refresh on billing date

### Can I change plans?

Yes! Upgrade or downgrade anytime:
- Upgrades: Immediate, prorated
- Downgrades: Effective next billing cycle

### How do I cancel?

1. Go to Account Settings
2. Click "Manage Subscription"
3. Select "Cancel Plan"

Your access continues until the end of your billing period.

### What payment methods are accepted?

- Credit/debit cards
- PayPal (select regions)

## Managing Your Account

### View Credit Balance

Find your balance in:
- Dashboard header
- Account settings
- User menu dropdown

### View Transaction History

1. Click your avatar
2. Select "Billing"
3. View "Transaction History"

### Get Receipts

Receipts are emailed automatically. Access past receipts in your billing portal.

## Getting Help

- **Billing questions**: {{site.email}}
- **Technical issues**: Use in-app support
- **Account access**: Reset via email

---

**Questions?** Our support team is here to help!',
    'manual',
    '["subscription", "credits", "billing", "pricing", "faq"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP,
    100,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 11. Troubleshooting Guide
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'troubleshooting',
    'Troubleshooting Guide',
    'Solutions for common errors like "Insufficient credits", "Upload failed", and more.',
    E'# Troubleshooting Guide

Quick solutions for common issues you might encounter.

## Credit Issues

### "Insufficient Credits"

**Cause**: Not enough credits for the action.

**Solutions**:
1. Check your credit balance (top-right corner)
2. Purchase additional credits
3. Upgrade to a paid plan for monthly credits

### Credits Not Refreshing

**Cause**: Monthly credits reset on billing date, not month start.

**Solution**: Check your billing date in Account Settings. Credits reset on that day each month.

## Upload Issues

### "Upload Failed"

**Common causes and solutions**:

| Cause | Solution |
|-------|----------|
| File too large | Reduce file size (max 10MB) |
| Wrong format | Use JPG, PNG, or PDF |
| Poor connection | Check internet, retry |
| Browser issue | Clear cache, try different browser |

### Image Won''t Display

1. Wait for upload to complete (check progress)
2. Refresh the page
3. Try uploading again
4. Use a different image format

## Export Issues

### PDF Won''t Download

**Try these steps**:
1. Disable pop-up blockers
2. Check browser downloads folder
3. Try a different browser
4. Clear browser cache

### PDF Looks Wrong

**Common fixes**:
- Ensure all elements are within page bounds
- Check for hidden layers
- Preview before exporting
- Try "High Quality" export setting

## Editor Issues

### Page Won''t Load

1. Refresh the page (Ctrl/Cmd + R)
2. Clear browser cache
3. Try incognito/private mode
4. Check internet connection

### Changes Not Saving

**Auto-save** should handle this, but if issues persist:
1. Click "Save" manually
2. Check internet connection
3. Don''t close tab during save
4. Export a backup copy

### Elements Disappeared

1. Check layer panel (may be hidden)
2. Use Undo (Ctrl/Cmd + Z)
3. Check if elements moved off-page
4. Reload from last save

## AI Generation Issues

### AI Image Failed

**Possible causes**:
- Server busy - try again in a few minutes
- Prompt too complex - simplify your request
- Content policy - modify inappropriate content
- Credits not charged if generation fails

### Poor AI Results

**Improve results by**:
- Being more specific in prompts
- Using style presets
- Adding reference images
- Trying different wording

## Account Issues

### Can''t Log In

1. Check email/password are correct
2. Use "Forgot Password" to reset
3. Check for typos in email
4. Clear browser cookies
5. Contact support if still stuck

### Email Not Received

1. Check spam/junk folder
2. Verify email address is correct
3. Add our domain to safe senders
4. Request email resend

## Printing Issues

### Colors Look Different

**Solutions**:
- Calibrate monitor colors
- Use "Print Quality" export
- Test on same paper type
- Adjust printer color settings

### Pages Cut Off

1. Set scaling to 100% (not "fit to page")
2. Match paper size to export size
3. Check printer margins

## Browser Compatibility

### Supported Browsers

✅ Chrome (recommended)
✅ Firefox
✅ Safari
✅ Edge

❌ Internet Explorer (not supported)

### For Best Experience

- Keep browser updated
- Enable JavaScript
- Allow cookies
- Disable ad blockers on our site

## Still Need Help?

### Contact Support

- **Email**: {{site.email}}
- **In-app**: Click "Help" button
- **Response time**: Within {{support.response_hours}} hours

### When Contacting Support

Please include:
- Your account email
- Description of the issue
- Steps to reproduce
- Screenshots if helpful
- Browser and device info

---

**We''re here to help!** Don''t hesitate to reach out.',
    'manual',
    '["troubleshooting", "errors", "help", "support", "faq"]'::jsonb,
    NULL,
    true,
    true,
    CURRENT_TIMESTAMP,
    110,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- 12. Frequently Asked Questions
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'faq',
    'Frequently Asked Questions',
    'Quick answers to the most common questions about Make Decodables.',
    E'# Frequently Asked Questions

Quick answers to common questions about Make Decodables.

## General Questions

### What is Make Decodables?

Make Decodables is an online tool for creating foldable mini-books (8-page zines). It''s designed for teachers, parents, and storytellers to create engaging reading materials.

### Who is it for?

- **Teachers**: Create decodable readers and classroom materials
- **Parents**: Make personalized books for children
- **Homeschoolers**: Supplement curriculum
- **Authors**: Prototype story ideas
- **Anyone**: Create fun mini-books!

### Is it free to use?

Yes! We offer a free plan with {{tiers.t1.signupBonus}} bonus credits. Paid plans provide additional credits and features.

### What browsers are supported?

Chrome (recommended), Firefox, Safari, and Edge. Internet Explorer is not supported.

## Creating Books

### How many pages are in a mini-book?

Each mini-book has **8 pages**:
- 1 cover
- 6 inside pages
- 1 back cover

### Can I create longer books?

Currently, each project creates an 8-page book. For longer content, create multiple books as a series.

### What file formats can I export?

- **PDF**: Best for printing
- **PNG/JPG**: Individual page images

### Can I use my own images?

Yes! Upload your own images in JPG, PNG, or PDF format (max 10MB each).

## AI Features

### How does AI image generation work?

Describe what you want, select a style, and our AI creates a unique illustration. Each generation costs {{creditCosts.ai_image}} credits.

### Are AI-generated images unique?

Yes! Each generation creates a new, unique image based on your prompt.

### What is Smart Scan/OCR?

OCR (Optical Character Recognition) converts images of text into editable text. Great for digitizing handwriting or printed materials.

## Credits & Billing

### What are credits?

Credits are the currency for AI features. Different features cost different amounts (usually {{creditCosts.ai_image}} credits each).

### Do unused credits roll over?

- **Monthly credits**: No, they reset each billing cycle
- **Permanent credits**: Yes, they never expire

### Can I cancel my subscription?

Yes, anytime. You''ll keep access until your billing period ends.

### What payment methods do you accept?

Credit cards, debit cards, and PayPal (in select regions).

## Printing

### What paper should I use?

Standard 24-28 lb printer paper works well. For durability, use cardstock.

### Can I use A4 paper?

Yes! Export in A4 size for non-US paper sizes.

### My print looks different from the screen?

This can happen due to monitor calibration. Do a test print before printing multiple copies.

## Account & Privacy

### Is my work saved automatically?

Yes, auto-save keeps your work safe. We also recommend manual saves before closing.

### Who can see my projects?

Your projects are private by default. Only you can see them unless you choose to publish to the marketplace.

### Can I delete my account?

Yes. Contact support to request account deletion. This removes all your data.

### How is my data protected?

We use encryption, secure servers, and follow industry best practices. See our [Privacy Policy](/privacy-policy) for details.

## Marketplace

### Can I sell my creations?

Yes! Publish templates and assets to the marketplace and earn credits when others purchase them.

### How much can I earn?

You receive {{marketplace.seller_share_percent}}% of each sale in credits. Popular creators can earn significant credits.

### What can I sell?

- Book templates
- Sticker packs
- Background sets
- Asset collections

## Technical Issues

### The editor isn''t loading

Try: Refresh page → Clear cache → Different browser → Contact support.

### I lost my work

Check auto-save history in the project menu. Contact support if needed.

### Export is failing

Ensure stable internet connection, try a different browser, or use a different quality setting.

---

**Still have questions?** Contact us at {{site.email}}',
    'manual',
    '["faq", "questions", "help", "answers", "general"]'::jsonb,
    NULL,
    true,
    true,
    CURRENT_TIMESTAMP,
    120,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);


-- ============================================================================
-- NEWS ARTICLES (6 articles)
-- ============================================================================

-- News 1: Platform Launch Announcement
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'welcome-to-make-decodables',
    'Welcome to Make Decodables - Create Beautiful Mini-Books',
    'We''re excited to announce the launch of Make Decodables, your new favorite tool for creating foldable mini-books.',
    E'# Welcome to Make Decodables!

We''re thrilled to announce the official launch of **Make Decodables** - the easiest way to create beautiful foldable mini-books!

## Our Mission

We built Make Decodables to empower teachers, parents, and storytellers to create engaging reading materials without needing design skills or expensive software.

## What Makes Us Special

### AI-Powered Creation

Our AI image generator creates unique illustrations from your descriptions. No more searching for the perfect clipart!

### Simple Folding Magic

One printed page transforms into an 8-page mini-book. It''s like magic, but it''s just clever folding!

### Educator-Friendly

Designed with K-12 educators in mind:
- Decodable reader templates
- Classroom-tested designs
- Easy batch printing

## Getting Started

1. **Sign up** for your free account
2. **Explore** our templates
3. **Create** your first book
4. **Print & fold** your masterpiece!

## What''s Included Free

- {{tiers.t1.signupBonus}} bonus credits
- Basic templates
- Export to PDF
- Community resources

## Join Our Community

Follow us for updates, tips, and inspiration:
- Share your creations with #MakeDecodables
- Join our educator Facebook group
- Subscribe to our newsletter

## Thank You

To our beta testers and early supporters - thank you for helping us shape Make Decodables. This launch is just the beginning!

**Ready to create?** [Start your first book now →](/dashboard)

---

*The Make Decodables Team*',
    'news',
    '["announcement", "launch", "welcome"]'::jsonb,
    NULL,
    true,
    true,
    CURRENT_TIMESTAMP - INTERVAL '30 days',
    10,
    156,
    CURRENT_TIMESTAMP - INTERVAL '30 days',
    CURRENT_TIMESTAMP - INTERVAL '30 days'
);

-- News 2: AI Image Generation Update
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'ai-image-generation-now-available',
    'New: AI Image Generation Now Available',
    'Create stunning illustrations with our new AI image generation feature. Just describe what you want!',
    E'# AI Image Generation Is Here!

We''re excited to announce our most requested feature: **AI Image Generation**!

## Create Custom Illustrations

No more searching through clip art libraries. Simply describe what you want, and our AI creates a unique illustration for your book.

### How It Works

1. Click the **AI Image** button
2. Describe your desired image
3. Choose a style (cartoon, watercolor, etc.)
4. Click generate!

### Example Prompts

- "A happy cat reading a book, cartoon style"
- "A cozy classroom with colorful decorations"
- "A rainbow over a garden of flowers"

## Style Options

Choose from multiple artistic styles:

- **Cartoon**: Bold, colorful, kid-friendly
- **Watercolor**: Soft, artistic, painterly
- **Flat Design**: Modern, clean, minimal
- **Sketch**: Hand-drawn, pencil-like
- **Pixel Art**: Retro, game-style

## Credits System

Each AI image generation costs **{{creditCosts.ai_image}} credits**. Failed generations don''t consume credits.

### Getting Credits

- Free accounts: {{tiers.t1.signupBonus}} bonus credits on signup
- Starter: {{tiers.t2.monthlyCredits}} monthly credits
- Pro: {{tiers.t3.monthlyCredits}} monthly credits
- Buy more anytime

## Tips for Great Results

1. **Be specific**: More detail = better results
2. **Use style presets**: Optimized for books
3. **Iterate**: Try multiple generations
4. **Reference images**: Upload inspiration

## Coming Soon

- More style options
- Batch generation
- Image editing tools
- Animation effects

## Try It Now

Open any project and click the AI Image button to try it out!

[Create with AI →](/dashboard)

---

*Happy creating!*
*The Make Decodables Team*',
    'news',
    '["feature", "ai", "update", "images"]'::jsonb,
    NULL,
    true,
    true,
    CURRENT_TIMESTAMP - INTERVAL '21 days',
    20,
    243,
    CURRENT_TIMESTAMP - INTERVAL '21 days',
    CURRENT_TIMESTAMP - INTERVAL '21 days'
);

-- News 3: Marketplace Launch
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'marketplace-now-open',
    'Marketplace Now Open: Share and Earn!',
    'Our community marketplace is live! Share your templates and earn credits when others use your creations.',
    E'# The Marketplace Is Open!

Introducing the **Make Decodables Marketplace** - a place to share your creations and discover amazing templates from fellow creators.

## What Is the Marketplace?

A community-driven store where you can:
- **Buy** templates and assets from other creators
- **Sell** your own creations and earn credits
- **Discover** new ideas and inspiration

## What''s Available?

### Templates
- Story book templates
- Educational worksheets
- Activity books
- Themed collections

### Assets
- Sticker packs
- Background sets
- Border collections
- Illustration bundles

## For Creators: How to Sell

1. Create your template or asset
2. Click "Publish to Marketplace"
3. Set your price (in credits)
4. Write a description and add previews
5. Submit for review

### Earning Credits

- You earn **{{marketplace.seller_share_percent}}%** of each sale
- Credits go to your permanent balance
- Use credits for AI features or purchases

## For Buyers: How to Shop

1. Browse the marketplace
2. Preview items before buying
3. Purchase with your credits
4. Instantly access in your library

## Quality Standards

All marketplace items are reviewed for:
- ✅ Original content
- ✅ Working functionality
- ✅ Appropriate content
- ✅ Accurate descriptions

## Featured Creators

We''ll spotlight top creators weekly:
- Most popular items
- New and notable
- Editor''s picks

## Launch Special

For our launch week:
- **20% bonus credits** on all purchases
- Featured placement for early sellers
- Community voting for best new items

## Browse Now

Ready to explore? Check out the marketplace!

[Visit Marketplace →](/marketplace)

---

*Share your creativity with the world!*
*The Make Decodables Team*',
    'news',
    '["announcement", "marketplace", "community", "feature"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP - INTERVAL '14 days',
    30,
    189,
    CURRENT_TIMESTAMP - INTERVAL '14 days',
    CURRENT_TIMESTAMP - INTERVAL '14 days'
);

-- News 4: User Story
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'teacher-spotlight-sarah-johnson',
    'Teacher Spotlight: How Sarah Uses Mini-Books in Her Classroom',
    'First-grade teacher Sarah Johnson shares how Make Decodables transformed her phonics instruction.',
    E'# Teacher Spotlight: Sarah Johnson

*How one first-grade teacher transformed her phonics instruction with mini-books*

## Meet Sarah

Sarah Johnson is a first-grade teacher in Austin, Texas. With 12 years of experience teaching early literacy, she''s always looking for engaging ways to help her students become confident readers.

## The Challenge

> "Finding decodable readers that matched exactly what I was teaching was always a struggle. Generic books didn''t align with my phonics sequence, and creating custom materials took hours."

## Discovering Make Decodables

Sarah found Make Decodables through a colleague''s recommendation.

> "The first time I created a mini-book in 15 minutes, I knew this would change everything. Now I make custom decodable readers that perfectly match my weekly phonics focus."

## Sarah''s Approach

### Weekly Routine

1. **Monday**: Create a new mini-book targeting the week''s phonics pattern
2. **Tuesday**: Print and fold as a class activity
3. **Wednesday-Friday**: Practice reading with partners
4. **Weekend**: Students take books home to share

### Student Favorites

- Personalized books with student names
- Silly stories featuring classroom mascot
- Non-fiction books about class topics

## Results

After one semester:
- **92%** of students meeting reading benchmarks (up from 78%)
- **Increased engagement** during phonics time
- **Parent involvement** increased with take-home books

## Sarah''s Tips

### For New Users

1. Start simple - one book at a time
2. Use templates as starting points
3. Let students help choose topics
4. Make it a classroom routine

### Favorite Features

- AI image generation for unique illustrations
- Easy printing and folding
- Template library saves time

## In Her Own Words

> "Make Decodables isn''t just a tool - it''s transformed how I teach reading. My students are more engaged, and I have more time to focus on instruction instead of searching for materials."

## Share Your Story

Are you using Make Decodables in creative ways? We''d love to feature you!

[Submit Your Story →](/contact-us)

---

*Thank you, Sarah, for sharing your experience!*',
    'news',
    '["user-story", "education", "teachers", "showcase"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP - INTERVAL '7 days',
    40,
    87,
    CURRENT_TIMESTAMP - INTERVAL '7 days',
    CURRENT_TIMESTAMP - INTERVAL '7 days'
);

-- News 5: New Templates Announcement
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'new-spring-templates-collection',
    'New Spring Template Collection Now Available',
    'Celebrate the season with our new spring-themed templates - perfect for classroom activities and seasonal stories.',
    E'# New Spring Templates Are Here!

Spring has arrived, and so has our newest template collection! 🌸

## What''s New

### Spring Story Templates

Fresh templates perfect for seasonal storytelling:
- **Garden Adventures**: Follow seeds as they grow
- **Spring Animals**: Baby animals and their habitats
- **Weather Watchers**: Rain, sunshine, and rainbows
- **Butterfly Journey**: Metamorphosis story template

### Educational Templates

Curriculum-aligned options:
- **Plant Life Cycle**: Science-ready with labels
- **Spring Math**: Counting flowers, bees, and butterflies
- **Poetry Book**: Haiku and spring poem formats
- **Nature Journal**: Observation recording template

### Activity Books

Interactive fun:
- **Spring Scavenger Hunt**: Outdoor exploration guide
- **Easter Egg Patterns**: Math patterns practice
- **Flower Coloring Book**: Relaxation and creativity
- **Bug Identification**: Mini field guide

## Featured Template: Garden Adventures

Our most popular new template!

**Includes**:
- 8-page story structure
- Garden-themed illustrations
- Customizable text areas
- Matching sticker set

**Perfect for**:
- Reading groups
- Science integration
- Creative writing
- Take-home books

## Spring Sticker Pack

New stickers to match the season:
- 🌷 Flowers (tulips, daffodils, roses)
- 🦋 Insects (butterflies, bees, ladybugs)
- 🌱 Plants (seedlings, trees, grass)
- ☔ Weather (rain, sun, clouds, rainbows)
- 🐰 Animals (bunnies, chicks, birds)

## Seasonal Pricing

For a limited time:
- **Spring Bundle**: All templates + stickers for 50 credits (save 40%!)
- **Individual templates**: 10-25 credits each
- **Sticker pack only**: 20 credits

## How to Access

1. Go to Templates in your dashboard
2. Filter by "Spring" or "Seasonal"
3. Click to preview any template
4. Add to your project!

## Coming Soon

- Summer template collection (June)
- Back-to-school templates (August)
- Holiday collections (November-December)

## Share Your Spring Creations

Tag us @MakeDecodables to share your spring books!

[Explore Spring Templates →](/dashboard?category=spring)

---

*Happy Spring!* 🌼
*The Make Decodables Team*',
    'news',
    '["update", "templates", "seasonal", "spring"]'::jsonb,
    NULL,
    true,
    true,
    CURRENT_TIMESTAMP - INTERVAL '3 days',
    50,
    64,
    CURRENT_TIMESTAMP - INTERVAL '3 days',
    CURRENT_TIMESTAMP - INTERVAL '3 days'
);

-- News 6: Platform Update
INSERT INTO articles (
    id, slug, title, summary, content, category, tags, cover_image,
    is_featured, is_published, published_at, sort_order, view_count,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    'january-2026-platform-update',
    'January 2026 Platform Update: Performance & New Features',
    'This month''s update brings faster loading times, improved export quality, and several new features you''ve requested.',
    E'# January 2026 Platform Update

Here''s what''s new this month!

## Performance Improvements

### Faster Loading

- **Editor load time**: 40% faster
- **Image uploads**: 2x faster
- **PDF exports**: 30% faster

### Improved Reliability

- Better auto-save (every 30 seconds)
- Reduced server errors
- Improved mobile performance

## New Features

### 1. Undo/Redo History

Finally! Full undo/redo support:
- **Ctrl/Cmd + Z**: Undo
- **Ctrl/Cmd + Shift + Z**: Redo
- Up to 50 steps of history

### 2. Grid Snapping

Align elements perfectly:
- Toggle grid on/off
- Adjustable grid size
- Snap-to-grid option

### 3. Copy/Paste Between Pages

- Select elements
- Copy (Ctrl/Cmd + C)
- Navigate to another page
- Paste (Ctrl/Cmd + V)

### 4. Bulk Image Upload

Upload multiple images at once:
- Drag and drop multiple files
- Progress indicator for each
- Auto-organize in library

## Export Improvements

### Higher Quality PDFs

- Improved color accuracy
- Sharper text rendering
- Better image compression

### New Export Options

- **Print-ready PDF**: With crop marks and bleed
- **Web-optimized PDF**: Smaller file size
- **Individual PNG pages**: High-resolution

## Bug Fixes

Fixed issues reported by users:
- ✅ Text alignment in certain fonts
- ✅ Sticker rotation precision
- ✅ Export timeout on large projects
- ✅ Mobile touch responsiveness
- ✅ Credit display delay after purchase

## Coming Next Month

Preview of February updates:
- Collaboration features (beta)
- More AI style options
- Template folder organization
- Classroom account management

## Your Feedback Matters

Many of these improvements came from your suggestions!

[Submit Feedback →](/contact-us)

## Technical Notes

For developers and power users:
- API version: 3.12
- React 19.2 upgrade complete
- New CDN for faster asset loading

---

*Thank you for using Make Decodables!*
*The Engineering Team*',
    'news',
    '["update", "features", "performance", "changelog"]'::jsonb,
    NULL,
    false,
    true,
    CURRENT_TIMESTAMP - INTERVAL '1 day',
    60,
    42,
    CURRENT_TIMESTAMP - INTERVAL '1 day',
    CURRENT_TIMESTAMP - INTERVAL '1 day'
);


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


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Count articles by category
SELECT category, COUNT(*) as count
FROM articles
WHERE is_published = true
GROUP BY category;

-- List all articles with basic info
SELECT slug, title, category, is_featured, published_at
FROM articles
WHERE is_published = true
ORDER BY category, sort_order;

-- ============================================================================
-- END OF SEED DATA
-- ============================================================================

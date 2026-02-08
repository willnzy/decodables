-- ============================================================================
-- NEWS ARTICLES SEED FILE
-- ============================================================================
-- Contains: 6 news articles for the /news page
-- Split from: articles_seed.sql
-- Template variables: Uses {{variable}} syntax resolved at runtime
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
- Share your creations with #foliaz
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
)
ON CONFLICT (slug) DO UPDATE SET
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    content = EXCLUDED.content,
    tags = EXCLUDED.tags,
    is_featured = EXCLUDED.is_featured,
    is_published = EXCLUDED.is_published,
    sort_order = EXCLUDED.sort_order,
    updated_at = CURRENT_TIMESTAMP;

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
)
ON CONFLICT (slug) DO UPDATE SET
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    content = EXCLUDED.content,
    tags = EXCLUDED.tags,
    is_featured = EXCLUDED.is_featured,
    is_published = EXCLUDED.is_published,
    sort_order = EXCLUDED.sort_order,
    updated_at = CURRENT_TIMESTAMP;

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
)
ON CONFLICT (slug) DO UPDATE SET
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    content = EXCLUDED.content,
    tags = EXCLUDED.tags,
    is_featured = EXCLUDED.is_featured,
    is_published = EXCLUDED.is_published,
    sort_order = EXCLUDED.sort_order,
    updated_at = CURRENT_TIMESTAMP;

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
)
ON CONFLICT (slug) DO UPDATE SET
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    content = EXCLUDED.content,
    tags = EXCLUDED.tags,
    is_featured = EXCLUDED.is_featured,
    is_published = EXCLUDED.is_published,
    sort_order = EXCLUDED.sort_order,
    updated_at = CURRENT_TIMESTAMP;

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

Tag us @foliaz to share your spring books!

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
)
ON CONFLICT (slug) DO UPDATE SET
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    content = EXCLUDED.content,
    tags = EXCLUDED.tags,
    is_featured = EXCLUDED.is_featured,
    is_published = EXCLUDED.is_published,
    sort_order = EXCLUDED.sort_order,
    updated_at = CURRENT_TIMESTAMP;

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
)
ON CONFLICT (slug) DO UPDATE SET
    title = EXCLUDED.title,
    summary = EXCLUDED.summary,
    content = EXCLUDED.content,
    tags = EXCLUDED.tags,
    is_featured = EXCLUDED.is_featured,
    is_published = EXCLUDED.is_published,
    sort_order = EXCLUDED.sort_order,
    updated_at = CURRENT_TIMESTAMP;

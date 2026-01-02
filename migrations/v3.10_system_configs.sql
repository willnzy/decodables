-- ==========================================
-- v3.10: Global Dynamic Configuration System
-- 全局动态文案配置系统
-- ==========================================

-- 1. Create system_configs table
CREATE TABLE IF NOT EXISTS system_configs (
  key TEXT PRIMARY KEY,                           -- 唯一键名 (e.g., HOME_HERO_TITLE)
  value TEXT NOT NULL,                            -- 配置值 (支持纯文本或 JSON 字符串)
  value_type TEXT NOT NULL DEFAULT 'text',        -- 值类型: 'text', 'boolean', 'json', 'number'
  config_group TEXT NOT NULL DEFAULT 'general',   -- 分组: marketing, error_msg, feature_flag, etc.
  description TEXT,                               -- 备注说明 (给运营人员)
  is_active BOOLEAN DEFAULT true,                 -- 是否启用
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by TEXT REFERENCES profiles(id)         -- 最后修改人
);

-- 2. Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_system_configs_group ON system_configs(config_group);
CREATE INDEX IF NOT EXISTS idx_system_configs_active ON system_configs(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_system_configs_updated ON system_configs(updated_at DESC);

-- 3. Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_system_configs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_system_configs_updated_at ON system_configs;
CREATE TRIGGER trg_system_configs_updated_at
  BEFORE UPDATE ON system_configs
  FOR EACH ROW
  EXECUTE FUNCTION update_system_configs_timestamp();

-- 4. Enable RLS
ALTER TABLE system_configs ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies
-- Public read for active configs (for frontend consumption)
DROP POLICY IF EXISTS "Public can read active configs" ON system_configs;
CREATE POLICY "Public can read active configs" ON system_configs
  FOR SELECT USING (is_active = true);

-- Admin can manage all configs
DROP POLICY IF EXISTS "Admin can manage configs" ON system_configs;
CREATE POLICY "Admin can manage configs" ON system_configs
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM profiles 
      WHERE id = (SELECT auth.jwt() ->> 'sub') 
      AND role = 'admin'
    )
  );

-- 6. Insert sample data
INSERT INTO system_configs (key, value, value_type, config_group, description) VALUES
  -- Marketing Group
  ('HOME_HERO_TITLE', 'Create Beautiful 8-Page Zines in Minutes', 'text', 'marketing', 'Homepage hero section main title'),
  ('HOME_HERO_SUBTITLE', 'AI-powered story generation meets easy drag-and-drop editing. Perfect for teachers, parents, and creative minds.', 'text', 'marketing', 'Homepage hero section subtitle'),
  ('PRICING_TIP_PRO', 'Best for professional educators and content creators', 'text', 'marketing', 'Pro plan description tip on pricing page'),
  ('PRICING_TIP_STARTER', 'Great for educators getting started', 'text', 'marketing', 'Starter plan description tip on pricing page'),
  
  -- Feature Flags Group
  ('FEATURE_AI_GENERATION', 'true', 'boolean', 'feature_flag', 'Enable/disable AI image generation feature'),
  ('FEATURE_MARKETPLACE', 'true', 'boolean', 'feature_flag', 'Enable/disable marketplace feature'),
  ('FEATURE_OCR', 'true', 'boolean', 'feature_flag', 'Enable/disable OCR/Smart Scan feature'),
  ('FEATURE_ZIP_EXPORT', 'true', 'boolean', 'feature_flag', 'Enable/disable ZIP export feature'),
  
  -- Limits Group
  ('FREE_PROJECT_LIMIT', '1', 'number', 'limits', 'Maximum projects for free tier users'),
  ('STARTER_PROJECT_LIMIT', '20', 'number', 'limits', 'Maximum projects for starter tier users'),
  ('PRO_PROJECT_LIMIT', '200', 'number', 'limits', 'Maximum projects for pro tier users'),
  ('MAX_UPLOAD_FILE_SIZE_MB', '5', 'number', 'limits', 'Maximum file upload size in MB'),
  ('MAX_LISTING_PRICE', '500', 'number', 'limits', 'Maximum price for marketplace listings in credits'),
  
  -- Credits/Costs Group
  ('CREDITS_PER_IMAGE', '5', 'number', 'credits', 'Credits cost per AI generated image'),
  ('CREDITS_PER_OCR', '5', 'number', 'credits', 'Credits cost per OCR/Smart Scan'),
  ('CREDITS_PER_AI_DESIGN_PAGE', '5', 'number', 'credits', 'Credits cost per AI design page'),
  ('CREDITS_COST_WITH_REFERENCE', '7', 'number', 'credits', 'Credits cost for AI generation with reference image'),
  ('SIGNUP_BONUS_CREDITS', '50', 'number', 'credits', 'Permanent credits given to new users on signup'),
  
  -- Pricing Group
  ('CREDITS_PRICE_BASE', '4.99', 'number', 'pricing', 'Base price for 100 credits (USD)'),
  ('CREDITS_PRICE_PRO', '3.99', 'number', 'pricing', 'Discounted price for Pro users (USD)'),
  ('PRO_CREDITS_DISCOUNT_PERCENT', '20', 'number', 'pricing', 'Discount percentage for Pro users on credit purchases'),
  ('STARTER_PLAN_PRICE', '14.9', 'number', 'pricing', 'Monthly price for Starter plan (USD)'),
  ('PRO_PLAN_PRICE', '29.9', 'number', 'pricing', 'Monthly price for Pro plan (USD)'),
  ('STARTER_MONTHLY_CREDITS', '500', 'number', 'pricing', 'Monthly credits for Starter plan'),
  ('PRO_MONTHLY_CREDITS', '1000', 'number', 'pricing', 'Monthly credits for Pro plan'),
  
  -- Trial Group
  ('TRIAL_PERIOD_DAYS', '7', 'number', 'trial', 'Number of days for free trial period'),
  
  -- Error Messages Group
  ('ERROR_INSUFFICIENT_CREDITS', 'You don''t have enough credits. Please top up to continue.', 'text', 'error_msg', 'Shown when user has insufficient credits'),
  ('ERROR_UPLOAD_FAILED', 'Failed to upload file. Please try again or use a smaller file.', 'text', 'error_msg', 'Shown when file upload fails'),
  ('ERROR_FILE_TOO_LARGE', 'File too large. Maximum size is {size}MB', 'text', 'error_msg', 'Shown when uploaded file exceeds size limit'),
  ('ERROR_PROJECT_LIMIT_REACHED', 'Maximum {limit} projects reached. Upgrade to create more.', 'text', 'error_msg', 'Shown when user reaches project limit'),
  
  -- Notification Templates
  ('NOTIF_WELCOME', '{"title": "Welcome to Make Decodables!", "content": "Start creating your first zine today. We''ve given you 50 free credits to get started!"}', 'json', 'notification', 'Welcome notification template for new users'),
  
  -- UI Texts
  ('UI_UPGRADE_CTA', 'Upgrade Now', 'text', 'ui', 'Upgrade button text'),
  ('UI_TRIAL_BANNER', 'You have {days} days left in your free trial', 'text', 'ui', 'Trial period banner text (supports {days} placeholder)'),
  ('UI_TRIAL_EXPIRED', 'Your 7-day trial period has expired. This project is read-only.', 'text', 'ui', 'Trial expired message'),
  ('UI_TRIAL_EXPIRED_UPGRADE', 'Trial expired - Upgrade to continue', 'text', 'ui', 'Trial expired upgrade button text'),
  ('UI_UPGRADE_TO_STARTER', 'Upgrade to Starter', 'text', 'ui', 'Upgrade to Starter button text'),
  ('UI_UPGRADE_TO_PRO', 'Upgrade to Pro', 'text', 'ui', 'Upgrade to Pro button text'),
  ('UI_PUBLISH_PROMPT', 'Publish your projects to start earning credits', 'text', 'ui', 'Dashboard prompt to publish projects'),
  ('UI_CREDITS_LABEL_TOTAL', 'Total Credits', 'text', 'ui', 'Label for total credits'),
  ('UI_CREDITS_LABEL_MONTHLY', 'Monthly Credits', 'text', 'ui', 'Label for monthly credits'),
  ('UI_CREDITS_LABEL_PERMANENT', 'Permanent Credits', 'text', 'ui', 'Label for permanent credits'),
  ('UI_CREDITS_ABBREVIATION_MONTHLY', 'Monthly', 'text', 'ui', 'Abbreviation for monthly credits'),
  ('UI_CREDITS_ABBREVIATION_PERMANENT', 'Permanent', 'text', 'ui', 'Abbreviation for permanent credits'),
  
  -- File Upload Hints
  ('UI_UPLOAD_HINT_IMAGE', 'JPG, PNG, GIF, WebP · Max {size}MB', 'text', 'ui', 'File type hint for image upload'),
  ('UI_UPLOAD_HINT_IMAGE_SVG', 'JPG, PNG, GIF, WebP, SVG · Max {size}MB', 'text', 'ui', 'File type hint for image upload with SVG'),
  ('UI_UPLOAD_HINT_IMAGE_PDF', 'Images (JPG, PNG, WebP) or PDF · Max {size}MB', 'text', 'ui', 'File type hint for image/PDF upload'),
  ('UI_UPLOAD_HINT_REFERENCE', 'PNG, JPG, WebP · Max {size}MB', 'text', 'ui', 'File type hint for reference image upload'),
  ('UI_UPLOAD_HINT_REFERENCE_COMPACT', 'JPG/PNG/WebP|Max {size}MB', 'text', 'ui', 'Compact file type hint with pipe as line separator'),
  ('UI_UPLOAD_HINT_FEEDBACK', 'Max 5 images, {size}MB each', 'text', 'ui', 'File type hint for feedback image upload'),
  
  -- File Upload Error Messages  
  ('ERROR_INVALID_IMAGE_TYPE', 'Please upload JPG, PNG, or WebP image', 'text', 'error_msg', 'Error when invalid image type uploaded'),
  ('ERROR_INVALID_IMAGE_TYPE_FULL', 'Please upload an image file (PNG, JPG, WebP)', 'text', 'error_msg', 'Error when invalid image type uploaded (full format)'),
  ('ERROR_INVALID_IMAGE_TYPE_ALL', 'Only JPG, PNG, GIF, WebP images are allowed', 'text', 'error_msg', 'Error when invalid image type uploaded (all formats)'),
  
  -- Plan Feature Descriptions
  ('PLAN_FEATURE_STARTER_PROJECTS', 'Up to 20 projects', 'text', 'plan_features', 'Starter plan project limit description'),
  ('PLAN_FEATURE_PRO_PROJECTS', 'Up to 200 projects', 'text', 'plan_features', 'Pro plan project limit description'),
  ('PLAN_FEATURE_PRO_CREDITS_DISCOUNT', '20% off credits', 'text', 'plan_features', 'Pro plan credit discount description'),
  ('PLAN_FEATURE_ZIP_EXPORT', 'ZIP Export', 'text', 'plan_features', 'ZIP export feature description'),
  ('PLAN_FEATURE_OCR', 'Smart Scan (OCR)', 'text', 'plan_features', 'OCR feature description'),
  ('PLAN_FEATURE_COMMERCIAL_LICENSE', 'Commercial License', 'text', 'plan_features', 'Commercial license feature description'),
  ('PLAN_FEATURE_PERSONAL_UPLOAD', 'Personal Asset Upload', 'text', 'plan_features', 'Personal upload feature description'),
  ('PLAN_FEATURE_PROJECT_TEMPLATES', 'Project Templates', 'text', 'plan_features', 'Project templates feature description'),
  
  -- ==========================================
  -- Toast Success Messages
  -- ==========================================
  ('TOAST_TEMPLATE_SAVED', '✨ Template saved!', 'text', 'toast', 'Toast when template is saved'),
  ('TOAST_TEMPLATE_DELETED', 'Template deleted', 'text', 'toast', 'Toast when template is deleted'),
  ('TOAST_DESIGN_GENERATED', 'Design generated! Select and Import to apply.', 'text', 'toast', 'Toast when AI design is generated'),
  ('TOAST_AI_IDEA_CREATED', '✨ AI created a new idea for you!', 'text', 'toast', 'Toast when AI inspiration is generated'),
  ('TOAST_IMAGE_SAVED', 'Image saved to My Assets', 'text', 'toast', 'Toast when image is saved to assets'),
  ('TOAST_IMAGE_ADDED', 'Image added to page', 'text', 'toast', 'Toast when image is added to page'),
  ('TOAST_CONFIG_UPDATED', 'Configuration updated successfully', 'text', 'toast', 'Toast when config is updated'),
  ('TOAST_CONFIG_CREATED', 'Configuration created successfully', 'text', 'toast', 'Toast when config is created'),
  ('TOAST_CONFIG_DELETED', 'Configuration deleted', 'text', 'toast', 'Toast when config is deleted'),
  ('TOAST_CACHE_INVALIDATED', 'Cache invalidated successfully', 'text', 'toast', 'Toast when cache is invalidated'),
  ('TOAST_SAVED_SUCCESS', 'Saved successfully!', 'text', 'toast', 'Generic save success toast'),
  ('TOAST_LISTING_UPDATED', 'Listing updated successfully!', 'text', 'toast', 'Toast when marketplace listing is updated'),
  ('TOAST_FEEDBACK_EARNED', '+5 credits earned!', 'text', 'toast', 'Toast when user earns credits from feedback'),
  
  -- ==========================================
  -- Toast Warning Messages
  -- ==========================================
  ('TOAST_MAX_IMAGES_REACHED', 'Maximum {max} images allowed', 'text', 'toast', 'Toast when max images limit reached'),
  ('TOAST_VOICE_NOT_SUPPORTED', 'Voice input is not supported in your browser. Please use Chrome or Edge.', 'text', 'toast', 'Toast when voice input not supported'),
  ('TOAST_FILL_REQUIRED_FIELDS', 'Please fill in all required fields.', 'text', 'toast', 'Toast when required fields are empty'),
  ('TOAST_WAIT_BEFORE_SENDING', 'Please wait a moment before sending another message.', 'text', 'toast', 'Toast rate limit warning'),
  ('TOAST_SIGN_IN_TO_GENERATE', 'Please sign in to generate images', 'text', 'toast', 'Toast when user needs to sign in'),
  
  -- ==========================================
  -- Toast Error Messages
  -- ==========================================
  ('TOAST_TEMPLATE_SAVE_FAILED', 'Failed to save template', 'text', 'toast', 'Toast when template save fails'),
  ('TOAST_TEMPLATE_DELETE_FAILED', 'Failed to delete template', 'text', 'toast', 'Toast when template delete fails'),
  ('TOAST_FEEDBACK_SEND_FAILED', 'Failed to send feedback. Please try again.', 'text', 'toast', 'Toast when feedback send fails'),
  ('TOAST_SUPPORT_SEND_FAILED', 'Failed to send message. Please try again or contact us via WhatsApp.', 'text', 'toast', 'Toast when support message fails'),
  ('TOAST_CHECKOUT_FAILED', 'Failed to start checkout. Please try again.', 'text', 'toast', 'Toast when checkout fails'),
  ('TOAST_PORTAL_OPEN_FAILED', 'Unable to open subscription portal.', 'text', 'toast', 'Toast when portal open fails'),
  ('TOAST_PORTAL_FAILED', 'Failed to open subscription portal.', 'text', 'toast', 'Toast when portal fails'),
  ('TOAST_CONFIG_LOAD_FAILED', 'Failed to load configurations', 'text', 'toast', 'Toast when config load fails'),
  ('TOAST_CONFIG_KEY_REQUIRED', 'Config key is required', 'text', 'toast', 'Toast when config key is missing'),
  ('TOAST_CONFIG_DELETE_FAILED', 'Failed to delete configuration', 'text', 'toast', 'Toast when config delete fails'),
  ('TOAST_CONFIG_TOGGLE_FAILED', 'Failed to toggle configuration', 'text', 'toast', 'Toast when config toggle fails'),
  ('TOAST_CACHE_INVALIDATE_FAILED', 'Failed to invalidate cache', 'text', 'toast', 'Toast when cache invalidate fails'),
  ('TOAST_SETTING_UPDATE_FAILED', 'Failed to update setting', 'text', 'toast', 'Toast when setting update fails'),
  ('TOAST_SAVE_FAILED', 'Failed to save. Please try again.', 'text', 'toast', 'Generic save failed toast'),
  ('TOAST_PRESET_APPLY_FAILED', 'Failed to apply preset. Please try again.', 'text', 'toast', 'Toast when preset apply fails'),
  ('TOAST_UNPUBLISH_FAILED', 'Failed to unpublish. Please try again.', 'text', 'toast', 'Toast when unpublish fails'),
  ('TOAST_UPLOAD_FAILED', 'Upload failed: {error}', 'text', 'toast', 'Toast when upload fails with error'),
  ('TOAST_REPORT_SUBMIT_FAILED', 'Failed to submit report. Please try again.', 'text', 'toast', 'Toast when report submit fails'),
  
  -- ==========================================
  -- Error Messages (setError)
  -- ==========================================
  ('ERROR_SIGN_IN_TO_GENERATE', 'Please sign in to generate', 'text', 'error_msg', 'Error when user needs to sign in to generate'),
  ('ERROR_NOT_ENOUGH_CREDITS', 'Not enough credits', 'text', 'error_msg', 'Error when user has insufficient credits'),
  ('ERROR_CONTENT_POLICY', 'Content Policy Violation: Please modify your prompt', 'text', 'error_msg', 'Error for content policy violation'),
  ('ERROR_SELECT_DESIGN', 'Please select a design to import', 'text', 'error_msg', 'Error when no design is selected'),
  ('ERROR_SELECT_IMAGE_OR_PDF', 'Please select an image or PDF file', 'text', 'error_msg', 'Error when no file is selected'),
  ('ERROR_SELECT_PAGE_TO_SCAN', 'Please select at least one page to scan', 'text', 'error_msg', 'Error when no pages selected for scan'),
  ('ERROR_SIGN_IN_TO_CREATE_PROJECT', 'Please sign in to create a project', 'text', 'error_msg', 'Error when user needs to sign in to create project'),
  ('ERROR_PROJECT_LIMIT_MESSAGE', 'You have reached the maximum number of projects ({max}). Please upgrade to {plan} to create more projects.', 'text', 'error_msg', 'Error when project limit is reached'),
  ('ERROR_ENTER_PROMPT', 'Please enter a prompt or fill in the form', 'text', 'error_msg', 'Error when prompt is empty'),
  ('ERROR_ENTER_WHAT_TO_DRAW', 'Please enter what to draw', 'text', 'error_msg', 'Error when draw prompt is empty'),
  ('ERROR_DESCRIBE_CHARACTER', 'Please describe your character', 'text', 'error_msg', 'Error when character description is empty'),
  ('ERROR_SELECT_IMAGES_TO_SAVE', 'Please select at least one image to save', 'text', 'error_msg', 'Error when no images selected to save'),
  ('ERROR_TITLE_REQUIRED', 'Title is required', 'text', 'error_msg', 'Error when title is missing'),
  ('ERROR_DESCRIPTION_REQUIRED', 'Description is required', 'text', 'error_msg', 'Error when description is missing'),
  ('ERROR_STARTER_FREE_ONLY', 'Starter members can only publish free assets. Upgrade to Pro to set a price.', 'text', 'error_msg', 'Error for starter tier pricing restriction'),
  ('ERROR_GENERATION_FAILED', 'Generation failed. Please try again.', 'text', 'error_msg', 'Generic generation failed error'),
  ('ERROR_SCAN_FAILED', 'Scan failed. Please try again.', 'text', 'error_msg', 'Error when scan fails'),
  ('ERROR_PUBLISH_FAILED', 'Failed to publish. Please try again.', 'text', 'error_msg', 'Error when publish fails'),
  ('ERROR_SELECT_REPORT_REASON', 'Please select a report reason', 'text', 'error_msg', 'Error when report reason not selected'),
  ('ERROR_PROVIDE_REPORT_DETAILS', 'Please provide more details about the issue', 'text', 'error_msg', 'Error when report details are empty'),
  ('ERROR_ALREADY_REPORTED', 'You have already reported this item', 'text', 'error_msg', 'Error when item already reported'),
  ('ERROR_TEMPLATE_NAME_REQUIRED', 'Please enter a template name', 'text', 'error_msg', 'Error when template name is empty'),
  
  -- ==========================================
  -- Credits Display Texts
  -- ==========================================
  ('UI_CREDITS_PER_IMAGE', '{cost} Credits per image', 'text', 'ui', 'Credits cost per image display'),
  ('UI_CREDITS_PER_SCAN', '{cost} Credits per scan', 'text', 'ui', 'Credits cost per scan display'),
  ('UI_COST_CREDITS', 'Cost: {cost} credits', 'text', 'ui', 'Generic credits cost display'),
  ('UI_COST_PAGES_CREDITS', 'Cost: {cost} credits ({pages} pages × {per_page})', 'text', 'ui', 'Credits cost with pages breakdown'),
  ('UI_BALANCE_CREDITS', 'Balance: {balance} credits', 'text', 'ui', 'Credits balance display'),
  ('UI_BUY_CREDITS', 'Buy Credits', 'text', 'ui', 'Buy credits button text'),
  ('UI_CREDITS_100_PERMANENT', '100 permanent credits', 'text', 'ui', '100 permanent credits label'),
  ('UI_CREDITS_PER_100', '/ 100 credits', 'text', 'ui', 'Price per 100 credits label'),
  ('UI_CREDITS_NEVER_EXPIRE', '✨ All rewards are permanent credits (never expire)', 'text', 'ui', 'Permanent credits description'),
  
  -- ==========================================
  -- Feedback/Support UI Texts
  -- ==========================================
  ('UI_FEEDBACK_PROMO', '🎉 Get credits by sharing your feedback!', 'text', 'ui', 'Feedback promo banner text'),
  ('UI_FEEDBACK_EARN_CREDITS', 'Earn credits by sharing ideas!', 'text', 'ui', 'Feedback earn credits prompt'),
  ('UI_FEEDBACK_SUBMISSION_TITLE', 'Earn Submission Credits', 'text', 'ui', 'Feedback submission section title'),
  ('UI_FEEDBACK_SUBMISSION_DESC', 'Get {credits} permanent credits instantly!', 'text', 'ui', 'Feedback submission description'),
  ('UI_FEEDBACK_FEATURED_DESC', 'Receive +{credits} permanent credits!', 'text', 'ui', 'Featured feedback description'),
  ('UI_FEEDBACK_PLACEHOLDER', 'Please describe your feedback in detail...', 'text', 'ui', 'Feedback textarea placeholder'),
  ('UI_SUPPORT_FALLBACK', 'Sorry, I couldn''t connect. Please try WhatsApp (+1 725 290 0525) or email info@makedecodables.com', 'text', 'ui', 'Support chat fallback message'),
  
  -- ==========================================
  -- Project Related Texts
  -- ==========================================
  ('UI_PROJECT_READONLY_TRIAL', 'Your 7-day trial period has expired. This project is read-only.', 'text', 'ui', 'Trial expired project message'),
  ('UI_CREATE_PROJECT_TITLE', 'Create New Project', 'text', 'ui', 'Create project modal title'),
  ('UI_CREATE_PROJECT_DESC', 'Start a new zine project', 'text', 'ui', 'Create project modal description'),
  
  -- ==========================================
  -- Publish/Marketplace Texts
  -- ==========================================
  ('UI_PUBLISH_TITLE_REQUIRED', 'Title is required', 'text', 'ui', 'Publish form title required'),
  ('UI_PUBLISH_DESC_REQUIRED', 'Description is required', 'text', 'ui', 'Publish form description required'),
  ('UI_REPORT_WARNING', 'False reports may result in account restrictions. Please only report genuine issues.', 'text', 'ui', 'Report form warning'),
  ('UI_REPORT_PLACEHOLDER', 'Please provide any additional context about this report...', 'text', 'ui', 'Report form placeholder'),
  
  -- ==========================================
  -- Admin Panel Texts
  -- ==========================================
  ('UI_ADMIN_USER_CODE_MISMATCH', 'User code does not match. Please verify with the customer.', 'text', 'ui', 'Admin user verification error'),
  ('UI_ADMIN_VIEW_CREDITS', 'View your credits balance and upgrade options', 'text', 'ui', 'Credits dialog description'),
  ('UI_ADMIN_UPGRADE_TO_PURCHASE', 'Upgrade to purchase credits.', 'text', 'ui', 'Upgrade required for credits message'),
  ('UI_ADMIN_REFUND_CANCEL_HELP', 'For refunds or subscription cancellation, please contact support.', 'text', 'ui', 'Refund/cancel help text'),
  
  -- ==========================================
  -- Error Boundary Text
  -- ==========================================
  ('UI_ERROR_BOUNDARY_TITLE', 'Something went wrong', 'text', 'ui', 'Error boundary title'),
  ('UI_PREVIEW_LOAD_FAILED', 'Failed to load preview', 'text', 'ui', 'Preview load failed message'),
  
  -- ==========================================
  -- Additional Toast Messages (Round 2)
  -- ==========================================
  ('TOAST_IMAGE_SAVED_TO_ASSETS', 'Image saved to My Assets', 'text', 'toast', 'Toast when image saved to assets'),
  ('TOAST_IMAGE_ADDED_TO_PAGE', 'Image added to page', 'text', 'toast', 'Toast when image added to page'),
  ('TOAST_PORTAL_UNABLE_OPEN', 'Unable to open subscription portal.', 'text', 'toast', 'Toast when portal cannot open'),
  ('TOAST_PORTAL_FAILED', 'Failed to open subscription portal.', 'text', 'toast', 'Toast when portal fails to open'),
  ('TOAST_UPLOAD_FAILED', 'Upload failed: {error}', 'text', 'toast', 'Toast when upload fails'),
  ('TOAST_UNPUBLISH_FAILED', 'Failed to unpublish. Please try again.', 'text', 'toast', 'Toast when unpublish fails'),
  ('TOAST_LISTING_UPDATED', 'Listing updated successfully!', 'text', 'toast', 'Toast when listing is updated'),
  ('TOAST_SAVE_FAILED', 'Failed to save. Please try again.', 'text', 'toast', 'Toast when save fails'),
  
  -- ==========================================
  -- Additional Toast Messages (Round 3 - Editor Page)
  -- ==========================================
  ('TOAST_COPY_FAILED', 'Failed to copy', 'text', 'toast', 'Toast when copy fails'),
  ('TOAST_CREATE_PROJECT_FAILED', 'Failed to create project. Please try again.', 'text', 'toast', 'Toast when project creation fails'),
  ('TOAST_SAVE_TITLE_FAILED', 'Failed to save title', 'text', 'toast', 'Toast when title save fails'),
  ('TOAST_CANNOT_COPY_LOCKED_PAGE', 'Cannot copy to locked page', 'text', 'toast', 'Toast when trying to copy to locked page'),
  ('TOAST_SIGN_IN_TO_GENERATE', 'Please sign in to generate images', 'text', 'toast', 'Toast prompting sign in for generation'),
  ('TOAST_CONTENT_POLICY_VIOLATION', 'Content Policy Violation: Please modify your prompt and try again.', 'text', 'toast', 'Toast for content policy violation'),
  ('TOAST_GENERATION_FAILED', 'Generation failed. Please try again.', 'text', 'toast', 'Toast when generation fails'),
  ('TOAST_SIGN_IN_TO_EXPORT', 'Please sign in to export', 'text', 'toast', 'Toast prompting sign in for export'),
  ('TOAST_EXPORT_FAILED', 'Export failed. Please try again.', 'text', 'toast', 'Toast when PDF export fails'),
  ('TOAST_ZIP_EXPORT_FAILED', 'ZIP export failed. Please try again.', 'text', 'toast', 'Toast when ZIP export fails'),
  ('TOAST_UNABLE_GET_IMAGE_URL', 'Unable to get image URL', 'text', 'toast', 'Toast when image URL cannot be retrieved'),
  ('TOAST_LOCAL_IMAGE_UPLOAD_FIRST', 'Local images need to be uploaded first. Use "Upload > Save to My Assets".', 'text', 'toast', 'Toast for local image upload requirement'),
  ('TOAST_SAVE_TO_ASSETS_FAILED', 'Failed to save: {error}', 'text', 'toast', 'Toast when save to assets fails'),
  ('TOAST_SAVE_BEFORE_DUPLICATE', 'Please save the project first before duplicating', 'text', 'toast', 'Toast prompting save before duplicate'),
  ('TOAST_PROJECT_DUPLICATED', 'Project duplicated successfully!', 'text', 'toast', 'Toast when project is duplicated'),
  ('TOAST_DUPLICATE_PROJECT_FAILED', 'Failed to duplicate project. Please try again.', 'text', 'toast', 'Toast when project duplication fails'),
  ('TOAST_PRINT_FAILED', 'Print failed. Please try again.', 'text', 'toast', 'Toast when print fails'),
  ('TOAST_ASSET_PUBLISHED', 'Asset published successfully!', 'text', 'toast', 'Toast when asset is published'),
  ('TOAST_ASSET_UNPUBLISHED', 'Asset unpublished', 'text', 'toast', 'Toast when asset is unpublished'),
  ('TOAST_PROJECT_PUBLISHED', 'Project published successfully!', 'text', 'toast', 'Toast when project is published'),
  ('TOAST_SIGN_IN_TO_CONTINUE', 'Please sign in to continue', 'text', 'toast', 'Toast prompting sign in to continue'),
  
  -- ==========================================
  -- Additional Error Messages (Round 2)
  -- ==========================================
  ('ERROR_STARTER_PUBLISH_FREE_ONLY', 'Starter members can only publish free assets. Upgrade to Pro to set a price.', 'text', 'error_msg', 'Error for starter tier pricing restriction'),
  ('ERROR_ENTER_WHAT_TO_DRAW', 'Please enter what to draw', 'text', 'error_msg', 'Error when prompt is empty'),
  ('ERROR_NOT_ENOUGH_CREDITS', 'Not enough credits', 'text', 'error_msg', 'Error when credits are insufficient'),
  ('ERROR_SELECT_IMAGES_TO_SAVE', 'Please select at least one image to save', 'text', 'error_msg', 'Error when no images selected to save'),
  ('ERROR_TITLE_REQUIRED', 'Title is required', 'text', 'error_msg', 'Error when title is empty'),
  ('ERROR_DESCRIPTION_REQUIRED', 'Description is required', 'text', 'error_msg', 'Error when description is empty'),
  ('ERROR_PUBLISH_FAILED', 'Failed to publish. Please try again.', 'text', 'error_msg', 'Error when publish fails'),
  ('ERROR_CONTACT_FORM_FAILED', 'Failed to send message. Please try again or email us directly.', 'text', 'error_msg', 'Error when contact form fails')

ON CONFLICT (key) DO NOTHING;

-- 7. Create helper function to get config with default fallback
CREATE OR REPLACE FUNCTION get_config(config_key TEXT, default_value TEXT DEFAULT NULL)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  result TEXT;
BEGIN
  SELECT value INTO result
  FROM system_configs
  WHERE key = config_key AND is_active = true;
  
  RETURN COALESCE(result, default_value);
END;
$$;

-- 8. Create function to get configs by group
CREATE OR REPLACE FUNCTION get_configs_by_group(group_name TEXT)
RETURNS TABLE(key TEXT, value TEXT, value_type TEXT, description TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT sc.key, sc.value, sc.value_type, sc.description
  FROM system_configs sc
  WHERE sc.config_group = group_name AND sc.is_active = true
  ORDER BY sc.key;
END;
$$;

-- 9. Create audit log for config changes
CREATE TABLE IF NOT EXISTS config_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  config_key TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  action TEXT NOT NULL,  -- 'create', 'update', 'delete'
  changed_by TEXT REFERENCES profiles(id),
  changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_config_audit_key ON config_audit_logs(config_key);
CREATE INDEX IF NOT EXISTS idx_config_audit_time ON config_audit_logs(changed_at DESC);

-- Audit log RLS
ALTER TABLE config_audit_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admin can read audit logs" ON config_audit_logs;
CREATE POLICY "Admin can read audit logs" ON config_audit_logs
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM profiles 
      WHERE id = (SELECT auth.jwt() ->> 'sub') 
      AND role = 'admin'
    )
  );

DROP POLICY IF EXISTS "System can write audit logs" ON config_audit_logs;
CREATE POLICY "System can write audit logs" ON config_audit_logs
  FOR INSERT WITH CHECK (true);

COMMENT ON TABLE system_configs IS 'Global dynamic configuration system for app-wide settings and texts';
COMMENT ON TABLE config_audit_logs IS 'Audit trail for configuration changes';

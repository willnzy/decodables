--  SQL 
-- 

-- 1. 
SELECT 
    p.id as user_id,
    p.username,
    p.email,
    p.tier,
    COUNT(pr.id) as project_count
FROM profiles p
LEFT JOIN projects pr ON pr.user_id = p.id AND pr.is_deleted = false
WHERE p.username = 'YOUR_USERNAME_HERE'  -- 
GROUP BY p.id, p.username, p.email, p.tier;

-- 2. 
SELECT 
    p.id as user_id,
    p.username,
    p.email,
    p.tier,
    COUNT(pr.id) as project_count
FROM profiles p
LEFT JOIN projects pr ON pr.user_id = p.id AND pr.is_deleted = false
WHERE p.email = 'YOUR_EMAIL_HERE'  -- 
GROUP BY p.id, p.username, p.email, p.tier;

-- 3. （）
SELECT 
    p.id as user_id,
    p.username,
    p.email,
    p.tier,
    COUNT(pr.id) as project_count
FROM profiles p
LEFT JOIN projects pr ON pr.user_id = p.id AND pr.is_deleted = false
GROUP BY p.id, p.username, p.email, p.tier
ORDER BY project_count DESC;

-- 4. 10
SELECT 
    p.id as user_id,
    p.username,
    p.email,
    p.tier,
    COUNT(pr.id) as project_count
FROM profiles p
LEFT JOIN projects pr ON pr.user_id = p.id AND pr.is_deleted = false
GROUP BY p.id, p.username, p.email, p.tier
ORDER BY project_count DESC
LIMIT 10;


-- 查询用户项目数量的 SQL 脚本
-- 可以通过用户名或邮箱查找用户的项目数量

-- 1. 通过用户名查找用户的项目数量
SELECT 
    p.id as user_id,
    p.username,
    p.email,
    p.tier,
    COUNT(pr.id) as project_count
FROM profiles p
LEFT JOIN projects pr ON pr.user_id = p.id AND pr.is_deleted = false
WHERE p.username = 'YOUR_USERNAME_HERE'  -- 替换为实际用户名
GROUP BY p.id, p.username, p.email, p.tier;

-- 2. 通过邮箱查找用户的项目数量
SELECT 
    p.id as user_id,
    p.username,
    p.email,
    p.tier,
    COUNT(pr.id) as project_count
FROM profiles p
LEFT JOIN projects pr ON pr.user_id = p.id AND pr.is_deleted = false
WHERE p.email = 'YOUR_EMAIL_HERE'  -- 替换为实际邮箱
GROUP BY p.id, p.username, p.email, p.tier;

-- 3. 查看所有用户的项目数量（按项目数量排序）
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

-- 4. 查看项目数量最多的前10个用户
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


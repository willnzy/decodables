# API

## 

- **pytest**: Python 
- **pytest-asyncio**: 
- **httpx**: HTTP （ API ）

## 

```bash
# 
pytest

# 
pytest tests/test_tier_logic.py

# 
pytest -v

# 
pytest --cov=. --cov-report=html
```

## 

```
tests/
├── conftest.py              #  fixtures
├── test_tier_logic.py       # （）
├── test_projects_api.py     #  API 
├── test_export_api.py       #  API 
├── test_upload_api.py       #  API 
└── test_image_generation.py #  API 
```

##  (PRD v3.2)

### ✅ 

1. **test_tier_logic.py** - 
   - ✅ （Free: 1, Starter: 20, Pro: 200）
   - ✅ Free 7
   - ✅ （ZIP、、PDF）
   - ✅ AI （Free/Starter: flux-schnell, Pro: flux-dev）
   - ✅ （）

2. **test_projects_api.py** -  API 
   - ✅ 
   - ✅ Free 7
   - ✅ 

3. **test_export_api.py** -  API 
   - ✅ ZIP （Pro only）
   - ✅ PDF （ tier）

4. **test_upload_api.py** -  API 
   - ✅ （Pro only）

5. **test_image_generation.py** -  API 
   - ✅ AI （ tier）
   - ✅ Credit 

## 

1. **Mock **
   - Supabase:  `@patch('db_service.supabase')`
   - Clerk Auth: Mock `get_current_user`
   -  API: Mock HTTP 

2. ****
   -  mock
   -  `pytest.fixture` 

3. ****
   - 
   -  "test_[functionality]_[condition]" 

## 

1. ****: 
2. ****: （ mock）
3. ****:  mock 

## （）

 `test_tier_logic.py` ，：

```bash
pytest tests/test_tier_logic.py -v --ignore=tests/conftest.py
```


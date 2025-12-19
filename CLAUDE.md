# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GGStore (https://ggstore.com) Shopify 쇼핑몰 이미지 크롤러. Playwright 기반 동적 크롤링으로 모든 상품 이미지를 자동 수집.

## Commands

```bash
# Lint
ruff check src/ --fix

# Test (pytest-asyncio 자동 모드 설정됨)
pytest tests/ -v

# Run crawler
python -m src.main crawl

# Check status
python -m src.main status

# Show errors
python -m src.main errors

# Playwright browser install (required once)
python -m playwright install chromium
```

### 데이터 후처리 스크립트

```bash
# 이미지 URL CSV 생성 (중복 제거)
python scripts/process_image_urls.py

# 요약 보고서 생성
python scripts/generate_summary.py

# Google Sheets 업로드
python scripts/upload_to_google_sheets.py
```

## Architecture

```
src/
├── main.py              # CLI (crawl, status, errors 서브커맨드)
├── crawler.py           # GGStoreCrawler - Playwright 브라우저 자동화
├── parser.py            # GGStoreParser - HTML 파싱 (regex 기반)
├── downloader.py        # ImageDownloader - httpx 비동기 다운로드
├── models.py            # Pydantic 모델 (Product, ProductImage, CrawlResult)
├── checklist.py         # 작업 상태 모델 (JobStatus, JobType, ErrorType)
└── checklist_manager.py # 체크리스트 YAML 관리

scripts/
├── process_image_urls.py     # JSON → CSV 변환, 중복 제거
├── generate_summary.py       # 통계 보고서 생성
├── upload_to_google_sheets.py # Google Sheets API 연동
└── deduplicate_images.py     # 이미지 파일 중복 제거
```

**Data Flow**: `crawler.py` → `parser.py` → `downloader.py` → `data/`

## Key Patterns

- **Async context managers**: Crawler와 Downloader 모두 `async with` 패턴 사용
- **Pydantic models**: 모든 데이터 구조는 Pydantic BaseModel 기반
- **Regex parsing**: BeautifulSoup 없이 regex로 HTML 파싱 (parser.py)
- **Semaphore concurrency**: 다운로드 동시성 제어 (기본 5개)
- **Checklist tracking**: YAML 기반 작업 상태 추적 (세션, 작업, 에러 관리)

## Configuration

| Setting | Value |
|---------|-------|
| Python | 3.12+ |
| Line length | 100 |
| Ruff rules | E, F, I, UP |
| Request delay | 1.5초 (rate limiting) |
| Max concurrent downloads | 5 |
| pytest asyncio_mode | auto |

## Output Files

- `data/images/` - 다운로드된 상품 이미지
- `data/metadata.json` - 크롤링 결과 메타데이터
- `data/image_urls.json` - 추출된 이미지 URL 목록
- `data/image_urls_cleaned.csv` - Google Sheets용 CSV
- `store_parser_checklist.yaml` - 작업 진행 상태 추적

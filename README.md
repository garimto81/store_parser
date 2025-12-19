# GGStore Image Crawler

GGStore (https://ggstore.com) 쇼핑몰의 모든 상품 이미지를 자동으로 수집하는 크롤러입니다.

## Features

- Playwright 기반 동적 페이지 크롤링
- 모든 상품 이미지 자동 다운로드
- JSON 메타데이터 저장
- 중복 다운로드 방지 (증분 업데이트)
- 비동기 처리로 빠른 다운로드

## Requirements

- Python 3.12+
- Playwright
- Pydantic
- httpx

## Installation

```bash
# 의존성 설치
pip install playwright pydantic httpx

# Playwright 브라우저 설치
python -m playwright install chromium
```

## Usage

```bash
# 기본 실행
python -m src.main

# 옵션 지정
python -m src.main -o data/images -m data/metadata.json -d 2.0

# 브라우저 창 표시
python -m src.main --no-headless

# 디버그 모드
python -m src.main -v
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output` | 이미지 저장 디렉토리 | `data/images` |
| `-m, --metadata` | 메타데이터 파일 경로 | `data/metadata.json` |
| `-d, --delay` | 요청 간 딜레이 (초) | `1.5` |
| `--no-headless` | 브라우저 창 표시 | `False` |
| `--no-skip` | 기존 상품 재다운로드 | `False` |
| `-v, --verbose` | 디버그 로깅 활성화 | `False` |

## Output

### 이미지 파일
```
data/images/
├── product-name-1_01.jpg
├── product-name-1_02.jpg
├── product-name-2_01.jpg
└── ...
```

### 메타데이터 (data/metadata.json)
```json
{
  "products": [
    {
      "id": "product-name-1",
      "name": "Product Name",
      "url": "https://ggstore.com/products/...",
      "price": "$50.00",
      "category": "TEES",
      "images": [
        {
          "filename": "product-name-1_01.jpg",
          "original_url": "https://...",
          "local_path": "data/images/product-name-1_01.jpg",
          "downloaded_at": "2025-12-19T..."
        }
      ]
    }
  ],
  "total_products": 100,
  "total_images": 350
}
```

## Project Structure

```
ggp_store_parser/
├── src/
│   ├── __init__.py
│   ├── crawler.py      # Playwright 크롤러
│   ├── parser.py       # HTML 파싱
│   ├── downloader.py   # 이미지 다운로더
│   ├── models.py       # Pydantic 모델
│   └── main.py         # CLI 진입점
├── data/
│   ├── images/         # 다운로드된 이미지
│   └── metadata.json   # 메타데이터
├── docs/
│   └── PRD.md
├── pyproject.toml
└── README.md
```

## License

MIT

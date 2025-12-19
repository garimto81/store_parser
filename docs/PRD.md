# GGStore Image Crawler PRD

**Project**: ggp_store_parser
**Version**: 1.0.0
**Date**: 2025-12-19
**Author**: Claude Code

---

## 1. Overview

### 1.1 Purpose
GGStore(https://ggstore.com) 쇼핑몰의 모든 상품 이미지를 자동으로 수집하고 메타데이터와 함께 로컬에 저장하는 크롤러.

### 1.2 Goals
- 모든 상품 페이지에서 이미지 URL 추출
- 최고 해상도 이미지 다운로드
- 상품 정보를 JSON 메타데이터로 저장
- 중복 다운로드 방지 및 증분 업데이트 지원

### 1.3 Target Website
| 항목 | 값 |
|------|---|
| URL | https://ggstore.com |
| Platform | Shopify |
| CDN | `ggstore.com/cdn/shop/files/` |
| Categories | NEW ARRIVALS, TEES, SWEATS, HEADWEAR, ACCESSORIES, ALL |

---

## 2. Functional Requirements

### 2.1 Core Features

#### FR-01: 상품 목록 크롤링
- 메인 페이지 및 카테고리별 상품 목록 수집
- 페이지네이션 자동 처리
- 각 상품의 URL 추출

#### FR-02: 상품 상세 페이지 파싱
- 상품명, 가격, 카테고리 추출
- 모든 상품 이미지 URL 추출 (메인 이미지 + 서브 이미지)
- 최고 해상도 URL 생성 (width 파라미터 제거 또는 최대값 설정)

#### FR-03: 이미지 다운로드
- 비동기 다운로드로 성능 최적화
- 파일명 규칙: `{product_id}_{index}.jpg`
- 중복 체크 (이미 다운로드된 이미지 스킵)

#### FR-04: 메타데이터 저장
- JSON 형식으로 저장
- 크롤링 시간, 상품 정보, 이미지 경로 포함
- 증분 업데이트 지원

### 2.2 Optional Features
- [ ] CLI 인터페이스
- [ ] 스케줄링 (주기적 크롤링)
- [ ] 이미지 변경 감지

---

## 3. Technical Specifications

### 3.1 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.12+ |
| Browser Automation | Playwright | Latest |
| Data Validation | Pydantic | 2.x |
| HTTP Client | httpx | Latest |
| Package Manager | uv | Latest |

### 3.2 Project Structure

```
ggp_store_parser/
├── src/
│   ├── __init__.py
│   ├── crawler.py          # Playwright 크롤러
│   ├── parser.py           # HTML 파싱 로직
│   ├── downloader.py       # 이미지 다운로더
│   └── models.py           # Pydantic 데이터 모델
├── data/
│   ├── images/             # 다운로드된 이미지
│   └── metadata.json       # 메타데이터
├── tests/
│   └── test_crawler.py
├── docs/
│   └── PRD.md
├── pyproject.toml
└── README.md
```

### 3.3 Data Models

```python
class ProductImage(BaseModel):
    filename: str
    original_url: str
    local_path: str
    downloaded_at: datetime

class Product(BaseModel):
    id: str
    name: str
    url: str
    price: str | None
    category: str | None
    images: list[ProductImage]
    crawled_at: datetime

class CrawlResult(BaseModel):
    products: list[Product]
    crawled_at: datetime
    total_products: int
    total_images: int
```

---

## 4. Architecture

### 4.1 Flow Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Crawler       │────▶│   Parser        │────▶│   Downloader    │
│   (Playwright)  │     │   (Extract)     │     │   (Save)        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Navigate to   │     │   Extract       │     │   Download      │
│   product pages │     │   image URLs    │     │   images        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │   Save JSON     │
                                                │   metadata      │
                                                └─────────────────┘
```

### 4.2 Crawling Strategy

1. **Initial Load**: 메인 페이지 → `/collections/all` 접근
2. **Pagination**: 무한 스크롤 또는 페이지 파라미터로 전체 상품 로드
3. **Product Details**: 각 상품 페이지 방문하여 이미지 수집
4. **Rate Limiting**: 요청 간 적절한 딜레이 (1-2초)

### 4.3 Image URL Processing

Shopify CDN URL 패턴:
```
Original: //ggstore.com/cdn/shop/files/image.jpg?v=1234&width=600
High-res: https://ggstore.com/cdn/shop/files/image.jpg?v=1234
```

- `width` 파라미터 제거하여 원본 해상도 획득
- `//` prefix를 `https://`로 변환

---

## 5. Implementation Plan

### Phase 1: 기본 구조 (Day 1)
- [x] 프로젝트 구조 생성
- [x] PRD 문서 작성
- [ ] pyproject.toml 설정
- [ ] 데이터 모델 정의

### Phase 2: 크롤러 개발 (Day 2-3)
- [ ] Playwright 크롤러 구현
- [ ] 상품 목록 파싱
- [ ] 페이지네이션 처리

### Phase 3: 다운로더 개발 (Day 4)
- [ ] 이미지 다운로드 로직
- [ ] 메타데이터 저장
- [ ] 중복 체크

### Phase 4: 테스트 및 최적화 (Day 5)
- [ ] 단위 테스트
- [ ] E2E 테스트
- [ ] 성능 최적화

---

## 6. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Bot 차단 | High | User-Agent 설정, 딜레이 추가 |
| 사이트 구조 변경 | Medium | 선택자 모듈화, 에러 핸들링 |
| 대용량 이미지 | Low | 비동기 다운로드, 청크 처리 |

---

## 7. Success Criteria

- [ ] 전체 상품 이미지 95% 이상 수집
- [ ] 크롤링 완료 시간 10분 이내
- [ ] 메타데이터 JSON 정상 생성
- [ ] 중복 없이 이미지 저장

---

## 8. Dependencies

```toml
[project.dependencies]
playwright = ">=1.40.0"
pydantic = ">=2.0.0"
httpx = ">=0.25.0"
```

---

## Changelog

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-12-19 | Initial PRD |

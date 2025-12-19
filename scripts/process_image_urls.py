"""
Image URLs JSON to Google Sheets CSV Processor

이 스크립트는 image_urls.json 파일을 읽어서:
1. 중복 제품 제거 (같은 ID의 제품)
2. 구글 시트용 CSV 파일 생성
3. 이미지 URL은 파이프(|)로 구분
"""

import csv
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def clean_url(url: str) -> str:
    """URL에서 개행 문자 제거"""
    return url.replace('\n', '').strip()


def extract_variant_id(url: str) -> str:
    """URL에서 variant ID 추출"""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    return query_params.get('variant', [''])[0]


def deduplicate_products(products: list[dict]) -> list[dict]:
    """
    중복 제품 제거
    - 같은 product ID를 가진 제품들을 하나로 통합
    - variant가 다른 경우 URL에 variant 정보 포함
    """
    unique_products = {}

    for product in products:
        product_id = product['id']

        if product_id not in unique_products:
            # 첫 번째 제품 등록
            product['url'] = clean_url(product['url'])
            product['variant_id'] = extract_variant_id(product['url'])
            unique_products[product_id] = product
        else:
            # 이미 있는 제품이면 이미지 URL 병합 (중복 제거)
            existing = unique_products[product_id]
            new_images = set(existing['image_urls'])
            new_images.update(product['image_urls'])
            existing['image_urls'] = list(new_images)
            existing['image_count'] = len(existing['image_urls'])

    return list(unique_products.values())


def create_csv(products: list[dict], output_path: Path):
    """CSV 파일 생성"""

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'Product ID',
            'Product Name',
            'Product URL',
            'Variant ID',
            'Image Count',
            'Image URLs'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for product in products:
            # 이미지 URL을 파이프(|)로 구분
            image_urls_str = ' | '.join(product['image_urls'])

            writer.writerow({
                'Product ID': product['id'],
                'Product Name': product['name'],
                'Product URL': product['url'],
                'Variant ID': product.get('variant_id', ''),
                'Image Count': product['image_count'],
                'Image URLs': image_urls_str
            })


def main():
    """메인 실행 함수"""

    # 경로 설정
    data_dir = Path(r'D:\AI\claude01\ggp_store_parser\data')
    input_file = data_dir / 'image_urls.json'
    output_file = data_dir / 'image_urls_cleaned.csv'

    print(f"[INFO] JSON 파일 읽기: {input_file}")

    # JSON 파일 읽기
    with open(input_file, encoding='utf-8') as f:
        products = json.load(f)

    print(f"[SUCCESS] 총 {len(products)}개 항목 로드")

    # 중복 제거
    print("[INFO] 중복 제품 제거 중...")
    unique_products = deduplicate_products(products)

    print(f"[SUCCESS] 중복 제거 완료: {len(unique_products)}개 고유 제품")
    print(f"[INFO] 제거된 중복: {len(products) - len(unique_products)}개")

    # CSV 생성
    print(f"[INFO] CSV 파일 생성: {output_file}")
    create_csv(unique_products, output_file)

    print("[SUCCESS] 완료!")
    print(f"\n출력 파일: {output_file}")

    # 통계 출력
    total_images = sum(p['image_count'] for p in unique_products)
    avg_images = total_images / len(unique_products) if unique_products else 0

    print("\n통계:")
    print(f"  - 고유 제품 수: {len(unique_products)}")
    print(f"  - 총 이미지 수: {total_images}")
    print(f"  - 제품당 평균 이미지: {avg_images:.1f}")


if __name__ == '__main__':
    main()

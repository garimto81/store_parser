"""
Image URLs 데이터 요약 생성기

CSV 파일을 읽어서 상세 통계를 생성합니다.
"""

import csv
from collections import Counter
from pathlib import Path


def generate_summary(csv_file_path: Path):
    """CSV 파일에서 통계 생성"""

    products = []

    with open(csv_file_path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append(row)

    # 기본 통계
    total_products = len(products)
    total_images = sum(int(p['Image Count']) for p in products)
    avg_images = total_images / total_products if total_products > 0 else 0

    # 이미지 수 분포
    image_counts = [int(p['Image Count']) for p in products]
    min_images = min(image_counts) if image_counts else 0
    max_images = max(image_counts) if image_counts else 0

    # 상위 5개 제품 (이미지 수 기준)
    top_5_products = sorted(products, key=lambda x: int(x['Image Count']), reverse=True)[:5]

    # 하위 5개 제품 (이미지 수 기준)
    bottom_5_products = sorted(products, key=lambda x: int(x['Image Count']))[:5]

    # 제품 카테고리 분석 (이름에서 추출)
    categories = []
    for p in products:
        name = p['Product Name'].upper()
        if 'HOODIE' in name or 'ZIP' in name:
            categories.append('Hoodie/Jacket')
        elif 'TEE' in name or 'T-' in name:
            categories.append('T-Shirt')
        elif 'SWEATSHIRT' in name or 'CREW' in name:
            categories.append('Sweatshirt')
        elif 'CAP' in name:
            categories.append('Cap')
        elif 'JERSEY' in name:
            categories.append('Jersey')
        elif 'WINDBREAKER' in name:
            categories.append('Windbreaker')
        else:
            categories.append('Other')

    category_counts = Counter(categories)

    # 출력
    print("=" * 70)
    print("GGP Store 이미지 URL 데이터 요약")
    print("=" * 70)
    print()

    print("[기본 통계]")
    print(f"  총 제품 수: {total_products}")
    print(f"  총 이미지 수: {total_images}")
    print(f"  제품당 평균 이미지: {avg_images:.1f}")
    print(f"  최소 이미지 수: {min_images}")
    print(f"  최대 이미지 수: {max_images}")
    print()

    print("[제품 카테고리별 분포]")
    for category, count in category_counts.most_common():
        percentage = (count / total_products) * 100
        print(f"  {category:20s}: {count:2d}개 ({percentage:5.1f}%)")
    print()

    print("[이미지가 가장 많은 제품 TOP 5]")
    for i, product in enumerate(top_5_products, 1):
        print(f"  {i}. {product['Product Name'][:50]:50s} - {product['Image Count']:2s}개")
    print()

    print("[이미지가 가장 적은 제품 TOP 5]")
    for i, product in enumerate(bottom_5_products, 1):
        print(f"  {i}. {product['Product Name'][:50]:50s} - {product['Image Count']:2s}개")
    print()

    print("[파일 정보]")
    print(f"  CSV 파일: {csv_file_path}")
    print(f"  파일 크기: {csv_file_path.stat().st_size:,} bytes")
    print()

    print("=" * 70)
    print("데이터 활용 방법은 UPLOAD_GUIDE.md 참조")
    print("=" * 70)


def main():
    """메인 실행 함수"""
    csv_file = Path(r'D:\AI\claude01\ggp_store_parser\data\image_urls_cleaned.csv')

    if not csv_file.exists():
        print(f"[ERROR] CSV 파일이 없습니다: {csv_file}")
        return

    generate_summary(csv_file)


if __name__ == '__main__':
    main()

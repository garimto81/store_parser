"""
중복 이미지 URL 제거 스크립트

동일한 상품명을 가진 항목들을 병합하고 중복 URL을 제거합니다.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def deduplicate_image_urls(input_path: Path, output_path: Path) -> dict:
    """
    이미지 URL 중복 제거 및 상품 병합

    Args:
        input_path: 원본 JSON 파일 경로
        output_path: 출력 JSON 파일 경로

    Returns:
        통계 정보 딕셔너리
    """
    # 원본 데이터 로드
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    # 상품명 기준으로 그룹화
    products_by_name = defaultdict(list)
    for item in data:
        products_by_name[item["name"]].append(item)

    # 중복 제거 및 병합
    deduplicated = []
    original_image_count = 0
    unique_image_count = 0

    for name, items in products_by_name.items():
        # 첫 번째 항목을 기준으로 병합
        merged = {
            "id": items[0]["id"],
            "name": name,
            "url": items[0]["url"]
        }

        # 모든 이미지 URL 수집
        all_urls = []
        for item in items:
            all_urls.extend(item.get("image_urls", []))
            original_image_count += len(item.get("image_urls", []))

        # 중복 제거 (순서 유지)
        unique_urls = []
        seen = set()
        for url in all_urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)

        merged["image_urls"] = unique_urls
        merged["image_count"] = len(unique_urls)
        unique_image_count += len(unique_urls)

        deduplicated.append(merged)

    # 정렬 (상품명 기준)
    deduplicated.sort(key=lambda x: x["name"])

    # 결과 저장
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(deduplicated, f, ensure_ascii=False, indent=2)

    # 통계 계산
    reduction_rate = (
        ((original_image_count - unique_image_count) / original_image_count * 100)
        if original_image_count > 0
        else 0
    )

    return {
        "original_entries": len(data),
        "deduplicated_entries": len(deduplicated),
        "original_images": original_image_count,
        "unique_images": unique_image_count,
        "reduction_rate": f"{reduction_rate:.2f}%"
    }


def main():
    """메인 실행 함수"""
    start_time = datetime.now()

    # 경로 설정
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / "data" / "image_urls.json"
    output_path = base_dir / "data" / "image_urls_deduplicated.json"
    result_path = base_dir / ".agent" / "results" / "result-002.yaml"

    print(f"[{start_time.strftime('%H:%M:%S')}] 중복 제거 시작...")
    print(f"  입력: {input_path}")
    print(f"  출력: {output_path}")

    # 중복 제거 실행
    stats = deduplicate_image_urls(input_path, output_path)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 결과 출력
    print(f"\n[{end_time.strftime('%H:%M:%S')}] 완료!")
    print(f"  원본 항목: {stats['original_entries']}")
    print(f"  병합 후 항목: {stats['deduplicated_entries']}")
    print(f"  원본 이미지: {stats['original_images']}")
    print(f"  고유 이미지: {stats['unique_images']}")
    print(f"  감소율: {stats['reduction_rate']}")
    print(f"  소요 시간: {duration:.2f}초")

    # YAML 결과 생성
    result_path.parent.mkdir(parents=True, exist_ok=True)

    yaml_content = f"""task_id: task-002
agent_id: agent-coder-001
status: completed
started_at: {start_time.isoformat()}
completed_at: {end_time.isoformat()}
duration_seconds: {duration:.2f}

result:
  summary: |
    이미지 URL 중복 제거 완료.
    {stats['original_entries']}개 항목 → {stats['deduplicated_entries']}개 병합,
    {stats['original_images']}개 이미지 → {stats['unique_images']}개 고유
    ({stats['reduction_rate']} 감소)
  data:
    original_entries: {stats['original_entries']}
    deduplicated_entries: {stats['deduplicated_entries']}
    original_images: {stats['original_images']}
    unique_images: {stats['unique_images']}
    reduction_rate: "{stats['reduction_rate']}"

files_changed:
  - path: data/image_urls_deduplicated.json
    action: created

errors: []
"""

    with open(result_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"\n결과 저장: {result_path}")


if __name__ == "__main__":
    main()

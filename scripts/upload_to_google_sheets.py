"""
Google Sheets Uploader

CSV 파일을 구글 시트로 업로드합니다.
Google Sheets API를 사용합니다.
"""

import csv
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def upload_csv_to_sheets(csv_file_path: Path, spreadsheet_name: str = "GGP Store Image URLs"):
    """
    CSV 파일을 구글 시트로 업로드

    Args:
        csv_file_path: CSV 파일 경로
        spreadsheet_name: 생성할 스프레드시트 이름
    """

    # Google Sheets API 스코프
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]

    try:
        # Service Account 인증 (credentials.json 필요)
        credentials_path = Path(r'D:\AI\claude01\ggp_store_parser\credentials.json')

        if not credentials_path.exists():
            print("[ERROR] credentials.json 파일이 없습니다.")
            print(
                "구글 클라우드 콘솔에서 Service Account를 생성하고 "
                "credentials.json을 다운로드하세요."
            )
            print(f"경로: {credentials_path}")
            return None

        creds = service_account.Credentials.from_service_account_file(
            str(credentials_path),
            scopes=SCOPES
        )

        # Google Sheets API 서비스 생성
        service = build('sheets', 'v4', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)

        # CSV 파일 읽기
        print(f"[INFO] CSV 파일 읽기: {csv_file_path}")
        values = []
        with open(csv_file_path, encoding='utf-8-sig') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                values.append(row)

        print(f"[SUCCESS] {len(values)}행 읽기 완료 (헤더 포함)")

        # 스프레드시트 생성
        print(f"[INFO] 스프레드시트 생성: {spreadsheet_name}")
        spreadsheet = {
            'properties': {
                'title': spreadsheet_name
            }
        }

        spreadsheet = service.spreadsheets().create(
            body=spreadsheet,
            fields='spreadsheetId,spreadsheetUrl'
        ).execute()

        spreadsheet_id = spreadsheet.get('spreadsheetId')
        spreadsheet_url = spreadsheet.get('spreadsheetUrl')

        print("[SUCCESS] 스프레드시트 생성 완료")
        print(f"ID: {spreadsheet_id}")
        print(f"URL: {spreadsheet_url}")

        # 데이터 업로드
        print("[INFO] 데이터 업로드 중...")
        body = {
            'values': values
        }

        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A1',
            valueInputOption='RAW',
            body=body
        ).execute()

        print(f"[SUCCESS] {result.get('updatedCells')}개 셀 업데이트 완료")

        # 헤더 행 서식 지정
        print("[INFO] 서식 적용 중...")

        # 헤더 볼드 처리
        requests = [
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.2,
                                'green': 0.2,
                                'blue': 0.2
                            },
                            'textFormat': {
                                'foregroundColor': {
                                    'red': 1.0,
                                    'green': 1.0,
                                    'blue': 1.0
                                },
                                'fontSize': 10,
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            },
            # 헤더 행 고정
            {
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': 0,
                        'gridProperties': {
                            'frozenRowCount': 1
                        }
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            },
            # 열 너비 자동 조정
            {
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': 0,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 6
                    }
                }
            }
        ]

        batch_update_request = {'requests': requests}
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=batch_update_request
        ).execute()

        print("[SUCCESS] 서식 적용 완료")

        # 공유 설정 (누구나 링크로 볼 수 있도록)
        print("[INFO] 공유 설정 중...")
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }

        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body=permission
        ).execute()

        print("[SUCCESS] 공유 설정 완료 (누구나 링크로 볼 수 있음)")
        print("\n=== 완료 ===")
        print(f"스프레드시트 URL: {spreadsheet_url}")

        return spreadsheet_url

    except HttpError as error:
        print(f"[ERROR] Google API 오류: {error}")
        return None
    except Exception as e:
        print(f"[ERROR] 예외 발생: {e}")
        return None


def main():
    """메인 실행 함수"""
    csv_file = Path(r'D:\AI\claude01\ggp_store_parser\data\image_urls_cleaned.csv')

    if not csv_file.exists():
        print(f"[ERROR] CSV 파일이 없습니다: {csv_file}")
        return

    print("=" * 60)
    print("Google Sheets 업로드")
    print("=" * 60)

    url = upload_csv_to_sheets(csv_file)

    if url:
        print(f"\n브라우저에서 열기: {url}")
    else:
        print("\n[ERROR] 업로드 실패")
        print("\n대안: CSV 파일을 직접 구글 시트로 가져오기")
        print("1. https://sheets.google.com 열기")
        print("2. '파일 > 가져오기' 선택")
        print(f"3. CSV 파일 업로드: {csv_file}")


if __name__ == '__main__':
    main()

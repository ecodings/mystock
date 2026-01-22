import yfinance as yf
import json
from datetime import datetime, timedelta
import pandas as pd

# Google Sheets에서 종목 코드 가져오기
SHEET_ID = '1AMJsDNUm0y_tFNC3zW3zbWPqFTovEyAl-cnhPnSokSo'
SHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

def get_stock_codes():
    """스프레드시트에서 고유한 종목 코드 추출"""
    df = pd.read_csv(SHEET_URL)
    
    # 디버깅: 전체 구조 출력
    print(f"총 행 수: {len(df)}")
    print(f"총 컬럼 수: {len(df.columns)}")
    print(f"컬럼 이름: {df.columns.tolist()}")
    print(f"\n첫 5행 데이터:")
    print(df.head())
    
    # 모든 컬럼을 확인해서 종목 코드 찾기
    print("\n각 컬럼의 샘플 데이터:")
    for i, col in enumerate(df.columns):
        print(f"컬럼 {i} ({col}): {df.iloc[0, i]}")
    
    # 6번째 컬럼 (인덱스 6) 확인
    if len(df.columns) > 6:
        print(f"\n6번째 컬럼 데이터: {df.iloc[:, 6].unique()}")
    
    # 일단 빈 리스트 반환
    return []

def get_prev_close(code):
    """특정 종목의 전일 종가 가져오기"""
    try:
        ticker = f"{code}.KS"  # 코스피
        stock = yf.Ticker(ticker)
        
        # 최근 5일 데이터 가져오기
        hist = stock.history(period="5d")
        
        if len(hist) >= 2:
            # 마지막에서 두번째 날의 종가
            prev_close = hist['Close'].iloc[-2]
            return round(prev_close, 0)
        else:
            print(f"❌ {code}: 데이터 부족")
            return None
            
    except Exception as e:
        # 코스피 실패시 코스닥 시도
        try:
            ticker = f"{code}.KQ"
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                return round(prev_close, 0)
            else:
                return None
        except:
            print(f"❌ {code}: {e}")
            return None

def main():
    print("🔄 전일 종가 업데이트 시작...")
    
    # 종목 코드 가져오기
    codes = get_stock_codes()
    print(f"📊 총 {len(codes)}개 종목 발견")
    
    # 각 종목의 전일 종가 조회
    prices = {}
    for code in codes:
        price = get_prev_close(code)
        if price:
            prices[code] = price
            print(f"✅ {code}: {price:,}원")
    
    # JSON 파일로 저장
    data = {
        'updated_at': datetime.now().isoformat(),
        'prices': prices
    }
    
    with open('stock_prices.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ 완료! {len(prices)}개 종목 가격 업데이트됨")
    print(f"📅 업데이트 시간: {data['updated_at']}")

if __name__ == '__main__':
    main()

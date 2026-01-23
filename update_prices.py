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
    
    # H열이 종목 코드 (0-based 인덱스로 7번)
    # 하지만 CSV 파싱 후 실제 컬럼명 확인 필요
    
    # 컬럼명으로 직접 찾기
    code_column = None
    for col in df.columns:
        # 'Colum'으로 시작하는 컬럼 찾기
        if 'Colum' in str(col):
            code_column = col
            break
    
    if code_column is None:
        print("❌ 종목 코드 컬럼을 찾을 수 없습니다")
        return []
    
    codes = df[code_column].unique()
    
    # 빈 값 및 숫자가 아닌 값 제거
    valid_codes = []
    for code in codes:
        if pd.notna(code):
            code_str = str(code).strip()
            # 6자리 숫자인지 확인
            if code_str.isdigit() and len(code_str) == 6:
                valid_codes.append(code_str)
    
    print(f"유효한 종목 코드: {valid_codes}")
    return valid_codes

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

import yfinance as yf
import json
from datetime import datetime, timedelta
import pandas as pd

# Google Sheets에서 종목 코드 가져오기
SHEET_ID = '1AMJsDNUm0y_tFNC3zW3zbWPqFTovEyAl-cnhPnSokSo'
SHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

def get_stock_codes():
    """스프레드시트에서 고유한 종목 코드 추출 (한국 + 미국)"""
    df = pd.read_csv(SHEET_URL)
    
    # 계좌 컬럼 찾기 (C열)
    account_column = df.columns[2] if len(df.columns) > 2 else None
    
    # 종목 코드 컬럼 찾기 (F열)
    code_column = df.columns[5] if len(df.columns) > 5 else None
    
    if code_column is None or account_column is None:
        print("❌ 필요한 컬럼을 찾을 수 없습니다")
        return {'korea': [], 'us': []}
    
    # 한국 종목과 미국 종목 분리
    korea_codes = []
    us_codes = []
    
    for idx, row in df.iterrows():
        if pd.notna(row[code_column]) and pd.notna(row[account_column]):
            account = str(row[account_column]).strip()
            code = str(row[code_column]).strip()
            
            if account == '미국':
                # 미국 티커 (알파벳)
                if code and not code.isdigit():
                    us_codes.append(code)
            else:
                # 한국 종목 (6자리 숫자)
                if code.isdigit() and len(code) == 6:
                    korea_codes.append(code)
    
    # 중복 제거
    korea_codes = list(set(korea_codes))
    us_codes = list(set(us_codes))
    
    print(f"📊 한국 종목: {korea_codes}")
    print(f"🇺🇸 미국 종목: {us_codes}")
    
    return {'korea': korea_codes, 'us': us_codes}

def get_korea_prev_close(code):
    """한국 종목의 전일 종가 가져오기"""
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

def get_us_prev_close(ticker):
    """미국 주식의 전일 종가 가져오기 (USD)"""
    try:
        stock = yf.Ticker(ticker)
        
        # 최근 5일 데이터 가져오기
        hist = stock.history(period="5d")
        
        if len(hist) >= 2:
            # 마지막에서 두번째 날의 종가 (USD)
            prev_close = hist['Close'].iloc[-2]
            return round(prev_close, 2)  # 소수점 2자리
        else:
            print(f"❌ {ticker}: 데이터 부족")
            return None
            
    except Exception as e:
        print(f"❌ {ticker}: {e}")
        return None

def main():
    print("🔄 전일 종가 업데이트 시작...")
    
    # 종목 코드 가져오기
    codes = get_stock_codes()
    korea_codes = codes['korea']
    us_codes = codes['us']
    
    print(f"📊 한국 종목 {len(korea_codes)}개, 미국 종목 {len(us_codes)}개 발견")
    
    # 각 종목의 전일 종가 조회
    prices = {}
    
    # 한국 종목
    for code in korea_codes:
        price = get_korea_prev_close(code)
        if price:
            prices[code] = price
            print(f"✅ {code}: {price:,}원")
    
    # 미국 종목
    for ticker in us_codes:
        price = get_us_prev_close(ticker)
        if price:
            prices[ticker] = price
            print(f"✅ {ticker}: ${price:.2f}")
    
    # JSON 파일로 저장
    data = {
        'updated_at': datetime.now().isoformat(),
        'prices': prices
    }
    
    with open('stock_prices.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ 완료! 총 {len(prices)}개 종목 가격 업데이트됨")
    print(f"   - 한국: {len([k for k in prices.keys() if k.isdigit()])}개")
    print(f"   - 미국: {len([k for k in prices.keys() if not k.isdigit()])}개")
    print(f"📅 업데이트 시간: {data['updated_at']}")

if __name__ == '__main__':
    main()

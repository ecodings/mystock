import yfinance as yf
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import pandas as pd
import time
import os

# Google Sheets에서 종목 코드 가져오기
SHEET_ID = '1AMJsDNUm0y_tFNC3zW3zbWPqFTovEyAl-cnhPnSokSo'
SHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0'

def load_existing_prices():
    """기존 stock_prices.json 파일 로드"""
    if os.path.exists('stock_prices.json'):
        try:
            with open('stock_prices.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📂 기존 파일 로드: {data.get('updated_at', '알 수 없음')}")
                return data
        except:
            return None
    return None

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
    
    print(f"📊 한국 종목: {len(korea_codes)}개")
    print(f"🇺🇸 미국 종목: {len(us_codes)}개")
    
    return {'korea': korea_codes, 'us': us_codes}

def get_korea_price_from_naver(code):
    """네이버 금융에서 한국 주식 현재가 크롤링 (1차 시도)"""
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print(f"   🌐 네이버 접속 시도: {code}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"   ✓ HTTP 응답: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 현재가 찾기 (여러 셀렉터 시도)
        selectors = [
            'div.rate_info div.today span.blind',
            'p.no_today span.blind',
            '#chart_area > div.rate_info > div > p.no_today > em > span.blind',
            'div.today span.no_today span.blind'
        ]
        
        for i, selector in enumerate(selectors):
            elements = soup.select(selector)
            print(f"   셀렉터 {i+1} ({selector}): {len(elements)}개 발견")
            
            if elements:
                for element in elements:
                    price_text = element.text.replace(',', '').strip()
                    print(f"   텍스트: '{price_text}'")
                    
                    # 숫자인지 확인
                    if price_text.replace('.', '').isdigit():
                        price = float(price_text)
                        print(f"   ✅ 가격 파싱 성공: {price}")
                        return {
                            'price': round(price, 0),
                            'source': 'naver',
                            'timestamp': datetime.now().isoformat()
                        }
        
        print(f"   ❌ 가격을 찾을 수 없음")
        
        # HTML 일부 저장 (디버깅용)
        with open(f'debug_{code}.html', 'w', encoding='utf-8') as f:
            f.write(response.text[:5000])  # 처음 5000자만
        print(f"   💾 HTML 샘플 저장: debug_{code}.html")
        
        return None
        
    except Exception as e:
        print(f"   ❌ 오류: {e}")
        return None

def get_us_price_from_naver(ticker):
    """네이버페이 증권에서 미국 주식/ETF 현재가 크롤링"""
    url = f"https://m.stock.naver.com/worldstock/stock/{ticker}/total"
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    }
    
    try:
        print(f"   🌐 네이버페이 접속 시도: {ticker}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"   ✓ HTTP 응답: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 가격 추출 (클래스명에 StockPriceInfo_close-price 포함)
        price_div = soup.select_one('div[class*="StockPriceInfo_close-price"]')
        
        if price_div:
            span = price_div.find('span')
            if span:
                price_text = span.text.strip().replace(',', '')
                print(f"   텍스트: '{price_text}'")
                
                if price_text.replace('.', '').isdigit():
                    price = float(price_text)
                    print(f"   ✅ 가격 파싱 성공: ${price}")
                    return {
                        'price': round(price, 2),
                        'source': 'naver',
                        'timestamp': datetime.now().isoformat()
                    }
        
        print(f"   ❌ 가격을 찾을 수 없음")
        return None
        
    except Exception as e:
        print(f"   ❌ 오류: {e}")
        return None

def get_korea_prev_close(code):
    """한국 종목 가격 가져오기 (네이버 → yfinance 순서)"""
    # 1차: 네이버 크롤링
    result = get_korea_price_from_naver(code)
    if result:
        print(f"✅ {code}: {result['price']:,.0f}원 (네이버)")
        return result
    
    # 2차: yfinance 백업
    try:
        ticker = f"{code}.KS"  # 코스피
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-1]
            # Yahoo는 전일 종가이므로 날짜를 하루 전으로
            prev_date = (datetime.now() - timedelta(days=1)).replace(hour=15, minute=30, second=0, microsecond=0)
            print(f"✅ {code}: {prev_close:,.0f}원 (Yahoo, 전일)")
            return {
                'price': round(prev_close, 0),
                'source': 'yahoo',
                'timestamp': prev_date.isoformat()
            }
        else:
            # 코스닥 시도
            ticker = f"{code}.KQ"
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-1]
                prev_date = (datetime.now() - timedelta(days=1)).replace(hour=15, minute=30, second=0, microsecond=0)
                print(f"✅ {code}: {prev_close:,.0f}원 (Yahoo KQ, 전일)")
                return {
                    'price': round(prev_close, 0),
                    'source': 'yahoo',
                    'timestamp': prev_date.isoformat()
                }
            else:
                print(f"❌ {code}: 데이터 없음")
                return None
                
    except Exception as e:
        print(f"❌ {code}: {e}")
        return None

def get_us_prev_close(ticker):
    """미국 주식의 가격 가져오기 (네이버 → yfinance 순서)"""
    # 1차: 네이버페이 크롤링
    result = get_us_price_from_naver(ticker)
    if result:
        print(f"✅ {ticker}: ${result['price']:.2f} (네이버)")
        return result
    
    # 2차: yfinance 백업
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-1]
            # Yahoo는 전일 종가이므로 날짜를 하루 전으로
            prev_date = (datetime.now() - timedelta(days=1)).replace(hour=16, minute=0, second=0, microsecond=0)
            print(f"✅ {ticker}: ${prev_close:.2f} (Yahoo, 전일)")
            return {
                'price': round(prev_close, 2),
                'source': 'yahoo',
                'timestamp': prev_date.isoformat()
            }
        else:
            print(f"❌ {ticker}: 데이터 부족")
            return None
            
    except Exception as e:
        print(f"❌ {ticker}: {e}")
        return None

def should_update(existing_data, code, new_result):
    """기존 데이터와 비교해서 업데이트 여부 결정 (날짜 기준)"""
    if not existing_data or 'price_details' not in existing_data:
        return True
    
    if code not in existing_data['price_details']:
        return True
    
    existing = existing_data['price_details'][code]
    existing_source = existing.get('source', 'unknown')
    new_source = new_result['source']
    existing_time = datetime.fromisoformat(existing.get('timestamp', '2000-01-01'))
    new_time = datetime.fromisoformat(new_result['timestamp'])
    
    # 같은 날짜 내에서
    if existing_time.date() == new_time.date():
        # 네이버 → Yahoo 업데이트는 금지
        if existing_source == 'naver' and new_source == 'yahoo':
            print(f"   ⏭️  같은 날 네이버 데이터 유지")
            return False
        
        # 네이버끼리는 더 최신 시간 선택
        if existing_source == 'naver' and new_source == 'naver':
            if new_time > existing_time:
                print(f"   🔄 더 최신 네이버 데이터로 업데이트")
                return True
            return False
        
        # Yahoo → 네이버는 항상 업데이트
        if new_source == 'naver':
            print(f"   ⬆️  네이버 데이터로 업그레이드")
            return True
        
        # Yahoo끼리는 더 최신 시간 선택
        return new_time > existing_time
    
    # 다른 날짜는 항상 업데이트 (더 최신 날짜)
    if new_time.date() > existing_time.date():
        print(f"   📅 새로운 날짜 데이터로 업데이트")
        return True
    
    return False

def main():
    print("=" * 60)
    print("🔄 주가 업데이트 시작")
    print(f"⏰ 현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 기존 데이터 로드
    existing_data = load_existing_prices()
    
    # 종목 코드 가져오기
    codes = get_stock_codes()
    korea_codes = codes['korea']
    us_codes = codes['us']
    
    print(f"\n📊 총 {len(korea_codes) + len(us_codes)}개 종목 조회")
    
    prices = {}
    price_details = {}
    
    # 기존 데이터 복사 (업데이트되지 않은 종목 유지)
    if existing_data and 'prices' in existing_data:
        prices = existing_data['prices'].copy()
    if existing_data and 'price_details' in existing_data:
        price_details = existing_data['price_details'].copy()
    
    updated_count = 0
    skipped_count = 0
    
    # 한국 종목
    print("\n[한국 주식 조회]")
    for code in korea_codes:
        result = get_korea_prev_close(code)
        if result:
            if should_update(existing_data, code, result):
                prices[code] = result['price']
                price_details[code] = result
                updated_count += 1
            else:
                skipped_count += 1
        time.sleep(0.3)  # 0.3초 대기 (네이버 차단 방지)
    
    # 미국 종목
    print("\n[미국 주식 조회]")
    for ticker in us_codes:
        result = get_us_prev_close(ticker)
        if result:
            if should_update(existing_data, ticker, result):
                prices[ticker] = result['price']
                price_details[ticker] = result
                updated_count += 1
            else:
                skipped_count += 1
        time.sleep(0.3)
    
    # JSON 파일로 저장 (상세 정보 포함)
    data = {
        'updated_at': datetime.now().isoformat(),
        'prices': prices,
        'price_details': price_details  # 각 종목의 출처와 시간 정보
    }
    
    with open('stock_prices.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"✨ 완료! 총 {len(prices)}개 종목")
    print(f"   - 업데이트: {updated_count}개")
    print(f"   - 스킵: {skipped_count}개")
    print(f"   - 한국: {len([k for k in prices.keys() if k.isdigit()])}개")
    print(f"   - 미국: {len([k for k in prices.keys() if not k.isdigit()])}개")
    print(f"📅 파일 저장 시각: {data['updated_at']}")
    print("=" * 60)

if __name__ == '__main__':
    main()

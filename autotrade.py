import os
from dotenv import load_dotenv
import json
import pyupbit
import pandas as pd
import ta
from datetime import datetime, timedelta
from openai import OpenAI
import time
import codecs
import requests

load_dotenv()

class EnhancedCryptoDataCollector:
    def __init__(self, ticker="KRW-BTC"):
        self.ticker = ticker
        self.access = os.getenv("UPBIT_ACCESS_KEY")
        self.secret = os.getenv("UPBIT_SECRET_KEY")
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.upbit = pyupbit.Upbit(self.access, self.secret)
        self.client = OpenAI()
        self.fear_greed_api = "https://api.alternative.me/fng/"
    
    """비트코인 관련 최신 뉴스 조회"""
    def get_crypto_news(self):
        try:
            base_url = "https://serpapi.com/search.json"
            params = {
                "engine" : "google_news",
                "q" : "bitcoin crypto trading",
                "api_key" : self.serpapi_key,
                "gl" : "us",  # 미국 뉴스
                "hl" : "en",  # 영어 뉴스
            }

            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                news_data = response.json()

                if "news_results" not in news_data:
                    return None
                
                processed_news = []
                for news in news_data["news_results"][:5]:  # 최신 뉴스 5개만 가져오기
                    processed_news.append({
                        "title": news.get("title", ""),
                        "link": news.get("link", ""),
                        "source": news.get("source", {}).get("name", ""),
                        "date": news.get("date", ""),
                        "snippet": news.get("snippet", "")
                    })

                print("\n=== Latest Crypto News ===")
                for news in processed_news:
                    print(f"Title: {news['title']}")
                    print(f"Source: {news['source']}")
                    print(f"Date: {news['date']}")

                return processed_news
            return None
        except Exception as e:
            print(f"Error getting crypto news: {e}")
            return None


    """공포탐욕지수 데이터 조회"""
    def get_fear_greed_index(self, limit=7):
        try:
            response = requests.get(f"{self.fear_greed_api}?limit={limit}")
            if response.status_code == 200:
                data = response.json()
                
                # 최신 공포탐욕지수 출력
                latest = data['data'][0]
                print("\n=== Fear & Greed Index ===")
                print(f"Current Value : {latest['value']} ({latest['value_classification']})")
    

                # 7일간의 데이터 가공
                processed_data = []
                for item in data['data']:
                    processed_data.append({
                        "date": datetime.fromtimestamp(int(item['timestamp'])).strftime("%Y-%m-%d"),
                        "value": int(item["value"]),
                        "classification": item["value_classification"]
                    })
                
                print("\n=== Fear & Greed Index History ===")
                print (f"processed_data: {processed_data}")

                # 추세 분석
                values = [int(item["value"]) for item in data['data']]
                avg_value = sum(values) / len(values)
                treand = "Improving" if values[0] > avg_value else "Deteriorating"

                print("\n=== Fear & Greed Index AVG ===")
                print(f"Avg: {avg_value:.2f}")   

                return {
                    "current" : {
                        "value" : int(latest["value"]),
                        "classification" : latest["value_classification"]
                    },
                    "history": processed_data,
                    "trend": treand,
                    "average": avg_value
                }
            return None
        except Exception as e:
            print(f"Error getting fear & greed index: {e}")
            return None


    """기술적 분석 지표 추가"""
    def add_technical_indicators(self, df):

        # 볼린저 밴드
        indicator_bb = ta.volatility.BollingerBands(close=df["close"])
        df["bb_high"] = indicator_bb.bollinger_hband()
        df["bb_mid"] = indicator_bb.bollinger_mavg()
        df["bb_low"] = indicator_bb.bollinger_lband()
        df['bb_pband'] = indicator_bb.bollinger_pband()  

        # RSI
        df["rsi"] = ta.momentum.RSIIndicator(close=df["close"]).rsi()

        # MACD
        macd = ta.trend.MACD(close=df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_diff"] = macd.macd_diff()

        # 이동평균선
        df["sma_5"] = ta.trend.SMAIndicator(close=df["close"], window=5).sma_indicator()
        df["sma_20"] = ta.trend.SMAIndicator(
            close=df["close"], window=20
        ).sma_indicator()
        df["sma_60"] = ta.trend.SMAIndicator(
            close=df["close"], window=60
        ).sma_indicator()
        df["sma_120"] = ta.trend.SMAIndicator(
            close=df["close"], window=120
        ).sma_indicator()

        # ATR
        df["atr"] = ta.volatility.AverageTrueRange(
            high=df["high"], low=df["low"], close=df["close"]
        ).average_true_range()

        return df


    def get_current_status(self):
        """현재 투자 상태 조회"""
        try:
            krw_balance = float(self.upbit.get_balance("KRW"))                 # 보유 현금
            crypto_balance = float(self.upbit.get_balance(self.ticker))        # 보유 암호화폐
            avg_buy_price = float(self.upbit.get_avg_buy_price(self.ticker))   # 평균 매수 단가
            current_price = float(pyupbit.get_current_price(self.ticker))      # 현재가

            print("\n=== Current Investment Status ===")
            print(f"보유 현금 : {krw_balance:,.0f} KRW")
            print(f"보유 암호화폐 : {crypto_balance:,.8f} {self.ticker}")
            print(f"평균 매수 단가 : {avg_buy_price:,.0f} KRW")
            print(f"현재가 : {current_price:,.0f} KRW")

            total_value = krw_balance + (crypto_balance * current_price)       # 총 자산 가치 (현금 + 암호화폐 가치)
            unrealized_profit = ((current_price - avg_buy_price) * crypto_balance) if crypto_balance > 0 else 0  # 미실현 손익
            profit_percentage = (((current_price - avg_buy_price) - 1) * 100) if crypto_balance > 0 else 0

            print(f"총 자산 가치 : {total_value:,.0f} KRW")
            print(f"미실현 손익 : {unrealized_profit:,.0f} KRW ({profit_percentage:.2f}%)")

            return {
                "krw_balance": krw_balance,
                "crypto_balance": crypto_balance,
                "avg_buy_price": avg_buy_price,
                "current_price": current_price,
                "total_value": total_value,
                "unrealized_profit": unrealized_profit,
                "profit_percentage": profit_percentage
            }
        
        except Exception as e:
            print(f"Error getting current status: {e}")
            return None

    """호가 데이터 조회"""
    def get_orderbook_data(self):
        try:
            orderbook = pyupbit.get_orderbook(ticker=self.ticker)

            if not orderbook or len(orderbook) == 0:
                return None

            ask_prices = []  # 매도 호가
            ask_sizes = []
            bid_prices = []  # 매수 호가
            bid_sizes = []

            # 오더북(호가창)에서 상위 5개 매수/매도 호가 정보를 추출 (5개가 실제 거래에 가장 영향을 줌)
            for unit in orderbook["orderbook_units"][:5]:
                ask_prices.append(unit["ask_price"])
                ask_sizes.append(unit["ask_size"])
                bid_prices.append(unit["bid_price"])
                bid_sizes.append(unit["bid_size"])
            
            print("\n=== Orderbook Data ===")
            print(f"Timestamp: {datetime.fromtimestamp(orderbook['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"ask_prices: {ask_prices}")
            print(f"bid_prices: {bid_prices}")

            return {
                "timestamp": datetime.fromtimestamp(
                    orderbook["timestamp"] / 1000
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "total_ask_size": float(orderbook["total_ask_size"]),
                "total_bid_size": float(orderbook["total_bid_size"]),
                "ask_prices": ask_prices,
                "ask_sizes": ask_sizes,
                "bid_prices": bid_prices,
                "bid_sizes": bid_sizes,
            }

        except Exception as e:
            print(f"Error getting orderbook data: {e}")
            return None

    """차트 데이터 수집"""
    def get_ohlcv_data(self):
        try:
            # 30일 일봉 데이터
            daily_data = pyupbit.get_ohlcv(self.ticker, interval="day", count=30)
            daily_data = self.add_technical_indicators(daily_data)

            # 24시간 봉 데이터
            hourly_data = pyupbit.get_ohlcv(self.ticker, interval="minute60", count=24)
            hour_data = self.add_technical_indicators(hourly_data)

            # DataFrame을 dict로 변환시 datetiem index 처리
            daily_data_dict = []
            for index, row in daily_data.iterrows():
                day_data = row.to_dict()
                day_data["date"] = index.strftime("%Y-%m-%d")
                daily_data_dict.append(day_data)

            hourly_data_dict = []
            for index, row in hourly_data.iterrows():
                hour_data = row.to_dict()
                hour_data["date"] = index.strftime("%Y-%m-%d %H:%M:%S")
                hourly_data_dict.append(hour_data)

            # 최신 기술적 지표 출력
            print ("\n=== Latest Technical Indicators ===")
            print (f"RSI: {daily_data['rsi'].iloc[-1]:.2f}")
            print (f"MACD: {daily_data['macd'].iloc[-1]:.2f}")
            print (f"BB Position: {daily_data['bb_pband'].iloc[-1]:.2f}")

            return {
                "daily_data": daily_data_dict[-7],  # 최근 7일 데이터
                "hourly_data": hourly_data_dict[-6],  # 최근 6시간 데이터
                "latest_indicators": {
                    "rsi": daily_data['rsi'].iloc[-1],
                    "macd": daily_data['macd'].iloc[-1],
                    "macd_signal": daily_data['macd_signal'].iloc[-1],
                    "bb_position": daily_data['bb_pband'].iloc[-1]
                }
            }

        except Exception as e:
            print(f"Error getting OHLCV data: {e}")
            return None
        
    def get_ai_analysis(self, analysis_data):
        """AI 분석 및 매매 신호 생성"""
        try:
            # 데이터 최적화
            optimized_data = {
                "current_status" : analysis_data["current_status"],
                "orderbook_data" : {
                    "timestamp": analysis_data["orderbook_data"]["timestamp"],
                    "total_ask_size": analysis_data["orderbook_data"]["total_ask_size"],
                    "total_bid_size": analysis_data["orderbook_data"]["total_bid_size"],
                    "ask_prices": analysis_data["orderbook_data"]["ask_prices"][:3],  # 상위 3개 호가만 사용
                    "bid_prices": analysis_data["orderbook_data"]["bid_prices"][:3],  # 상위 3개 호가만 사용
                },
                "ohlcv_data": analysis_data["ohlcv"],
                "fear_greed" : analysis_data["fear_greed"]
            }

            

            promt = """당신은 비트코인 투자 전문가입니다. 제공된 데이터를 분석하여 매매 결정을 내려주세요. :
                        분석 기준:
                        1. 현재 보유 현황 (현금/코인 보유량...)
                        2. 차트 / 기술적 지표 (RSI, MACD, 볼린저밴드..)
                        3. 호가창 정보 (매수/매도 세력...)
                        4. 공포 탐욕 지수 (Fear & Greed Index)
                        5. 비트코인 관련 최신 뉴스

                        Please consider the fiolloing key points:
                        - Fear & greed Index below 20 (Extreme Fear) may present buying opportunitiese.
                        - Fear & Greed Index above 80 (Extreme Greed) may present selling opportunities.
                        - The trend of the Fear & Greeed Index is also a crucial inidicator.

                        응답은 반드시 아래 JSON 형식으로만 제공하고, 모든 텍스트는 한글로 작성해주세요:
                        {
                            "decision": "buy/sell/hold",
                            "reason": "상세한 분석 근거를 한글로 설명",
                            "risk_level": "low/medium/high",
                            "confidence_score": 0-100
                        }"""
        
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {
                        "role": "system",
                        "content": promt
                    },
                    {
                        "role": "user",
                        "content": f"Market data for analysis: {json.dumps(optimized_data, ensure_ascii=False)}"
                    }
                ]
            )

            result_text = response.choices[0].message.content.strip()
            print(f"\n=== Raw AI Response ===\n{result_text}\n")

            #응답에서 JSON 부분만 추출
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    result = json.loads(json_str)
                else:
                    raise Exception("Failed to parse AI response")
            except json.JSONDecodeError:
                    # 3단계: 유니코드 이스케이프 처리
                    try:
                        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            # 유니코드 이스케이프 디코딩 시도
                            decoded_str = codecs.decode(json_str, 'unicode_escape')
                            result = json.loads(decoded_str)
                        else:
                            raise Exception("JSON 형식을 찾을 수 없습니다")
                    except Exception as e:
                        print(f"모든 파싱 방법 실패: {e}")
                        raise Exception("AI 응답 파싱에 실패했습니다")
            return result
        except Exception as e:
            print(f"Error in get_ai_analysis: {e}")
            return None
    
    def execute_trade(self, decision, confidence_score, feat_greed_value):
        """AI 결정에 따라 거래 실행"""
        try:
            if decision == "buy":
                print("매수합니다.")
                # TODO : 여기에 매수 로직 추가
            
            elif decision == "sell":
                print("매도합니다.")
                # TODO : 여기에 매도 로직 추가
                # current_price = pyupbit.get_current_price(self.ticker)  # 현재가 조회
                # sell_amount = (krw_amount / current_price) * 0.9995  # 수수료 0.05% 반영, 매도수량
                # res = self.upbit.sell_market_order(self.ticker, btc_amount)
                # print("매도 시도 " + res)
            else:
                print("hold 합니다.")
                # TODO : 여기에 매도/매수 하지 않는 로직 추가

        except Exception as e:
            print(f"Error in execute_trade: {e}")


def ai_trading():
    try:
        trader = EnhancedCryptoDataCollector("KRW-BTC")  # 원하는 암호화폐 티커로 초기화 (예: "KRW-BTC")

        # 1. 현재 투자 상태 조회
        current_status = trader.get_current_status()

        #2 . 호가 데이터 조회
        orderbook_data = trader.get_orderbook_data()

        # 3. 차트 데이터 수집
        ohlcv_data = trader.get_ohlcv_data()

        #4. 공포 탐욕지수 데이터 조회
        fear_greed_data = trader.get_fear_greed_index()

        #5 비트코인 관련 최신 뉴스 조회
        news_data = trader.get_crypto_news()

        #6. AI 분석을 위한 데이터 준비
        if all([current_status, orderbook_data, ohlcv_data]):
            analysis_data = {
                "current_status": current_status,
                "orderbook_data": orderbook_data,
                "ohlcv": ohlcv_data,
                "fear_greed": fear_greed_data
            }

            #7. AI 분석 실행
            ai_result = trader.get_ai_analysis(analysis_data)
            if ai_result:
                print("\n=== AI Analysis Result ===")
                print(json.dumps(ai_result, indent=2))

                # 8. 매매 실행
                trader.execute_trade(ai_result["decision"], ai_result["confidence_score"], fear_greed_data["current"]["value"])
    except Exception as e:
        print(f"Error in ai_trading: {e}")
            
if __name__ == "__main__":
    print("Starting Enhancesd Bitcoin Trading Bot with Fear & Greed Index...")
    print("Press Ctrl+C to stop")

    try:
        ai_trading()
    except KeyboardInterrupt:
        print("\nTrading bot stopped by user.")
    except Exception as e:
        print(f"Error in main execution: {e}")
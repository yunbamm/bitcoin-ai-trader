import os
from dotenv import load_dotenv

load_dotenv()

# 1. 업비트 차트 데이터 가져오기 (30일 데이터)
import pyupbit

ticker = "KRW-BTC"
df = pyupbit.get_ohlcv(ticker, count=30, interval="day")

# 2. openai에게 데이터 제공하고 판단받기
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-4.1",
    input=[
        {
            "role": "system",
            "content": [
                {
                    "type": "input_text",
                    "text": 'You are an expert in Bitcoin investing. Tell me whether to buy, sell, or hold at the moment based on the chart data provided. Response in Json format.\n\n\nResponse Example:\n{decision: "buy", "reason" : "some technical reason"}\n{decision: "sell", "reason" : "some technical reason"}\n{decision: "hold", "reason" : "some technical reason"}',
                }
            ],
        },
        {"role": "user", "content": [{"type": "input_text", "text": df.to_json()}]},
    ],
    text={
        "format": {
            "type": "json_object",
        }
    },
)

result = response.output[0].content[0].text
import json
result = json.loads(result)


# 3. 판단 결과에 따라 매매하기
import pyupbit

# 업비트 API 키 설정
access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")
upbit = pyupbit.Upbit(access, secret)

krw_amount = 100000  # 매수/매도 금액

print("#### AI decision: ", result["decision"].upper(), " ####")
print("#### Reason: " + result["reason"], " ####")

if result["decision"] == "buy":
    print("매수합니다.")
    # 여기에 매수 로직 추가

    res = uupbit.buy_market_order(ticker, krw_amount)  # 매수
    print("매수 시도 " + res)

elif result["decision"] == "sell":
    print("매도합니다.")

    # 여기에 매도 로직 추가
    current_price = pyupbit.get_current_price(ticker)  # 현재가 조회
    sell_amount = (krw_amount / current_price) * 0.9995  # 수수료 0.05% 반영, 매도수량
    res = upbit.sell_market_order(ticker, btc_amount)
    print("매도 시도 " + res)

else:
    print("hold 합니다.")
    # 여기에 매도/매수 하지 않는 로직 추가

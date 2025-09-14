from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager


client = Client('8i0MeHvKMfvwLFHKchzDcZqnHj3AvX8woM16YYpTFz1HJn3PpepUlp3Orjx9laSq', 'oTlkvAEux54N4jWNYt7ZuGbYyqh7iG1m3RcZSJUcK9Be7MTaBOqMSsgfyupqenKE')



# fetch 1 minute klines for the last day up until now
klines = client.get_historical_klines("BNBUSDT", Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
print(klines)
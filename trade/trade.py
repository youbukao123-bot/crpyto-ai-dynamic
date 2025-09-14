
import sys
import os
src_dir= os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.insert(0, src_dir)

from gateway.binance import BinanceSpotHttp, OrderStatus, OrderType, OrderSide
from utils.config import config
from trade.mm_trader import round_to

config.loads('../online_data/config/config.json')

def test():


    http_client = BinanceSpotHttp(api_key=config.api_key, secret=config.api_secret, proxy_host=config.proxy_host,
                                       proxy_port=config.proxy_port)

    order = http_client.cancel_oco_order(symbol='minausdt', orderListId=1234)
    print(order)
    exit()

    new_sell_order = http_client.place_order(symbol='minausdt'.upper(), order_side=OrderSide.SELL,
                                             order_type=OrderType.LIMIT, quantity=20, price=5.0, icebergQty=10)
    print(new_sell_order)
    exit()

    new_sell_order = http_client.place_oco_order(symbol='bnbusdt'.upper(), order_side=OrderSide.SELL,
                                                 stop_price=200, stop_limit_price=199, price=500, quantity=0.1)

    print(new_sell_order)
    exit()




    check_order = http_client.get_order('bnbusdt'.upper(), client_order_id='E8WumPoxBVhJxJ80spsk6n')
    print(check_order)
    exit()

    resp = http_client.get_oco_order(orderListId=45945882)
    print(resp)
    exit()





    check_order = http_client.get_order('algousdt'.upper(), client_order_id='x-A6SIDXVS16311420175001000003')
    print(check_order)
    exit()
    check_order = http_client.get_all_order(symbol="algousdt".upper())
    print(check_order)
    exit()




    new_sell_order = http_client.place_order(symbol='ftmusdt'.upper(), order_side=OrderSide.SELL,
                                             order_type=OrderType.LIMIT, quantity=860, price=1.881)

    print(new_sell_order)
    if new_sell_order and 'status' in new_sell_order and new_sell_order['status'] == OrderStatus.NEW.value:
        print('aaa')
    exit()

    print('cancel')

    check_order = http_client.get_order('sushiusdt'.upper(), client_order_id='x-A6SIDXVS16312284198851000002')
    print(check_order.get('status'))
    http_client.cancel_order(symbol="sushiusdt".upper(), client_order_id='and_e3a525ec99b940b086ba85ca1f407483')
    exit()


    '''
    'symbol':'SUSHIUSDT',
    'orderId':603783405,
    'orderListId':-1,
    'clientOrderId':'and_8036d8d53f5744a9b2c671554777072c',
    'price':'13.90000000',
    'origQty':'143.68900000',
    'executedQty':'0.00000000',
    'cummulativeQuoteQty':'0.00000000',
    'status':'CANCELED',
    'timeInForce':'GTC',
    'type':'LIMIT',
    'side':'SELL',
    'stopPrice':'0.00000000',
    'icebergQty':'0.00000000',
    'time':1628953557479,
    'updateTime':1628984112018,
    'isWorking':True,
    'origQuoteOrderQty':'0.00000000'
    
    'symbol':'SUSHIUSDT',
    'orderId':615925170,
    'orderListId':-1,
    'clientOrderId':'and_a1c6cffaf4f444fba87d7df0b6351b8c',
    'price':'13.65600000',
    'origQty':'115.10700000',
    'executedQty':'115.10700000',
    'cummulativeQuoteQty':'1572.19032100',
    'status':'FILLED',
    'timeInForce':'GTC',
    'type':'LIMIT',
    'side':'SELL',
    'stopPrice':'0.00000000',
    'icebergQty':'0.00000000',
    'time':1629461388217,
    'updateTime':1629461388217,
    'isWorking':True,
    'origQuoteOrderQty':'0.00000000'
        
    '''

    print('check order')
    check_order = http_client.get_order('sushiusdt'.upper(), client_order_id='and_e3a525ec99b940b086ba85ca1f407483')
    print(check_order.get('status'))

    if check_order and check_order.get('status'):
        print(check_order.get('status') == OrderStatus.CANCELED.value)
    exit()

    check_order = http_client.get_all_order(symbol="sushiusdt".upper())
    print(check_order)
    exit()



    sell_price = round_to(0.00089, 0.00001)
    print(sell_price)
    new_sell_order = http_client.place_order(symbol='winusdt'.upper(), order_side=OrderSide.SELL, order_type=OrderType.LIMIT, quantity=288975, price=sell_price)

    print(new_sell_order)
    exit()

    new_buy_order = http_client.place_order(symbol='adausdt'.upper(), order_side=OrderSide.SELL, order_type=OrderType.MARKET, quantity=8, price=1.1, quoteOrderQty=0.1)
    print('order')
    print(new_buy_order)
    if new_buy_order:
        print('in order')
        print(new_buy_order.get('executedQty'))

    # if new_buy_order:
    #     print('check order')
    #     check_order = http_client.get_order('adausdt'.upper(),  client_order_id=new_buy_order.get('clientOrderId'))
    #     print(check_order)
    exit()
    #
    # print(new_buy_order)
    #
    # exit()


'''
{
'orderListId':45945882,
'contingencyType':'OCO',
'listStatusType':'ALL_DONE',
'listOrderStatus':'ALL_DONE',
'listClientOrderId':'Sqs6wXnjwBuXxDEgIuMaSQ',
'transactionTime':1632584325493,
'symbol':'BNBUSDT',
'orders':[
{
'symbol':'BNBUSDT',
'orderId':3069131971,
'clientOrderId':'E8WumPoxBVhJxJ80spsk6n'
},
{
'symbol':'BNBUSDT',
'orderId':3069131972,
'clientOrderId':'s0XZEDJhwCqj6yF4w4QTmZ'
}
],
'orderReports':[
{
'symbol':'BNBUSDT',
'origClientOrderId':'E8WumPoxBVhJxJ80spsk6n',
'orderId':3069131971,
'orderListId':45945882,
'clientOrderId':'1sk0aZPFAISIBcXQNhuOLN',
'price':'199.00000000',
'origQty':'0.10000000',
'executedQty':'0.00000000',
'cummulativeQuoteQty':'0.00000000',
'status':'CANCELED',
'timeInForce':'GTC',
'type':'STOP_LOSS_LIMIT',
'side':'SELL',
'stopPrice':'200.00000000'
},
{
'symbol':'BNBUSDT',
'origClientOrderId':'s0XZEDJhwCqj6yF4w4QTmZ',
'orderId':3069131972,
'orderListId':45945882,
'clientOrderId':'1sk0aZPFAISIBcXQNhuOLN',
'price':'500.00000000',
'origQty':'0.10000000',
'executedQty':'0.00000000',
'cummulativeQuoteQty':'0.00000000',
'status':'CANCELED',
'timeInForce':'GTC',
'type':'LIMIT_MAKER',
'side':'SELL'
}
]
}

'''


def mail_test():
    import smtplib


if __name__ == '__main__':
    test()
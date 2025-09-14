from datetime import datetime
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import timedelta
from utils import file_utils
from utils.time_utils import *
import glob
from dateutil.relativedelta import relativedelta

pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.max_rows', 5000)  # 最多显示数据的行数

base_dir='..'
BINANCE_SPOT_DAT_COL = ['open_time', 'open', 'high', 'low', 'close', 'volumn', 'close_time', 'quote_volumn',
                        'trades',
                        'taker_base_volumn', 'taker_quote_volumn', 'ignore']

def cal_volumn_oneshot(start_time, end_time, cal_day_cycles, trade_time, dt_indexs=None, shift=1):
    target_coins = file_utils.read_file(f'{base_dir}/data/exchange_binance_all.txt')
    target_coins = [coin.lower() for coin in target_coins]
    print(len(target_coins))

    from datetime import datetime
    date_format = "%Y-%m-%d %H:%M:%S"
    start_day = datetime.strptime(start_time, date_format)
    end_day = datetime.strptime(end_time, date_format)
    days = (end_day - start_day).days
    hours = days * 24 + int((end_day - start_day).seconds / 3600)
    index = []
    for i in range(0, hours + 1):
        index.append((start_day + timedelta(hours=i)).strftime(date_format))
    date_index = pd.DataFrame(index, columns=['date_time'])

    coin_dfs = dict()
    for name in glob.glob(f'{base_dir}/data/spot_hour_binance/*'):
        coin = name.split('/')[-1].split('_')[0].lower()
        if coin not in target_coins:
            continue
        df = pd.read_csv(name) \
            .rename(columns={"openTime": "open_time"})

        df = df[df['open_time'] >= start_time]
        df = df[df['open_time'] <= end_time]

        if len(df) == 0:
            continue

        if coin not in coin_dfs:
            coin_dfs[coin] = df
        else:
            coin_dfs[coin] = coin_dfs[coin].append(df)

    vol_date_dict = {}
    for coin, df in coin_dfs.items():
        if True:
            df['open_time'] = pd.to_datetime(df['open_time']) - timedelta(hours=trade_time)  # **表示N点开始交易！！！
            df['open_time'] = df['open_time'].apply(lambda x: x.strftime(date_format))
            df['open_time_str'] = df['open_time']
            df.set_index('open_time', inplace=True)
            df.sort_index(inplace=True)
            df = df[~df.index.duplicated(keep='first')]

            # 补全数据
            # total_df['date_time'] = pd.to_datetime(total_df['date_time']) - timedelta(hours=trade_time) #**表示N点开始交易！！！
            total_df = pd.merge(date_index, df, how='left', left_on='date_time', right_on='open_time')
            total_df['date_time'] = pd.to_datetime(total_df['date_time'])
            total_df.set_index('date_time', inplace=True)
            total_df.sort_index(inplace=True)
            total_df = total_df.ffill()
            # total_df.to_csv("/Users/daonyu/Documents/workdesk/crypt_quant/test1.csv")

            #resample
            period_type = f'24H'
            cycle_df = total_df.resample(period_type).last()
            cycle_df['open'] = total_df['open'].resample(period_type).first()
            cycle_df['open_time'] = total_df['open_time_str'].resample(period_type).first()
            cycle_df['high'] = total_df['high'].resample(period_type).max()
            cycle_df['low'] = total_df['low'].resample(period_type).min()
            cycle_df['close'] = total_df['close'].resample(period_type).last()
            cycle_df['volumn'] = total_df['volumn'].resample(period_type).sum()
            cycle_df['quote_volumn'] = total_df['quote_volumn'].resample(period_type).sum()

            #shift
            cycle_df['quote_volumn_sum'] = cycle_df['quote_volumn'].rolling(cal_day_cycles).sum().shift(periods=shift)

            for dt in cycle_df.index.values:
                dt_str = numpy64_to_str(dt)[0:10]  # e.g.2020-12-29
                if dt_indexs and dt_str not in dt_indexs:
                    continue
                if dt_str not in vol_date_dict:
                    vol_date_dict[dt_str] = {}
                vol_date_dict[dt_str][coin] = cycle_df.loc[dt]['quote_volumn_sum']

    return vol_date_dict

def load_data(start_time, end_time, hour_cycle, trade_time):
    target_coins = file_utils.read_file(f'{base_dir}/data/exchange_binance_all.txt')
    target_coins = [coin.lower() for coin in target_coins]
    print(len(target_coins))

    from datetime import datetime
    date_format = "%Y-%m-%d %H:%M:%S"
    start_day = datetime.strptime(start_time, date_format)
    end_day = datetime.strptime(end_time, date_format)
    days = (end_day - start_day).days
    hours = days * 24 + int((end_day - start_day).seconds / 3600)
    index = []
    for i in range(0, hours + 1):
        index.append((start_day + timedelta(hours=i)).strftime(date_format))
    date_index = pd.DataFrame(index, columns=['date_time'])
    #date_index.set_index('date_time', inplace=True)
    #date_index.sort_index(inplace=True)

    coin_dfs = dict()
    for name in glob.glob(f'{base_dir}/data/spot_hour_binance/*'):
        coin = name.split('/')[-1].split('_')[0].lower()
        if coin not in target_coins:
            continue
        df = pd.read_csv(name) \
            .rename(columns={"openTime": "open_time"})

        df = df[df['open_time'] >= start_time]
        df = df[df['open_time'] <= end_time]

        if len(df) == 0:
            continue

        if coin not in coin_dfs:
            coin_dfs[coin] = df
        else:
            coin_dfs[coin] = coin_dfs[coin].append(df)

    legal_hours = len(coin_dfs['btcusdt'])
    remain_coins = {}
    for coin, df in coin_dfs.items():
        #try:
        if True:
            df['open_time'] = pd.to_datetime(df['open_time']) - timedelta(hours=trade_time) #**表示N点开始交易！！！
            df['open_time'] = df['open_time'].apply(lambda x: x.strftime(date_format))
            df.set_index('open_time', inplace=True)
            df.sort_index(inplace=True)
            df = df[~df.index.duplicated(keep='first')]

            #补全数据
            #total_df['date_time'] = pd.to_datetime(total_df['date_time']) - timedelta(hours=trade_time) #**表示N点开始交易！！！
            total_df = pd.merge(date_index, df, how='left', left_on='date_time', right_on='open_time')
            total_df['date_time'] = pd.to_datetime(total_df['date_time'])
            total_df.set_index('date_time', inplace=True)
            total_df.sort_index(inplace=True)
            total_df = total_df.ffill()
            #total_df.to_csv("/Users/daonyu/Documents/workdesk/crypt_quant/test1.csv")

            if coin == 'btcusdt':
                total_df.to_csv(f'{base_dir}/data/pools/test_btc.txt')
                print(total_df)
            #聚合
            period_type = f'{hour_cycle}H'
            cycle_df = total_df.resample(period_type).last()
            cycle_df['open'] = total_df['open'].resample(period_type).first()
            cycle_df['high'] = total_df['high'].resample(period_type).max()
            cycle_df['low'] = total_df['low'].resample(period_type).min()
            cycle_df['close'] = total_df['close'].resample(period_type).last()
            cycle_df['volumn'] = total_df['volumn'].resample(period_type).sum()
            cycle_df['quote_volumn'] = total_df['quote_volumn'].resample(period_type).sum()

            #cycle_df.to_csv("/Users/daonyu/Documents/workdesk/crypt_quant/test2.csv")
            #exit()

            if coin == 'btcusdt':
                print(cycle_df)
            remain_coins[coin] = cycle_df.loc[cycle_df.index[0]]['quote_volumn']
        # except:
        #     print(coin)
        #     continue
    print(len(remain_coins))
    #exit()
    return remain_coins

'''
    取每月前一周平均
'''
def rank_trade_amount_monthly():
    start_day = '2021-09-01'
    end_day = '2021-09-01'
    cycle = 7
    cur_start_day = start_day

    month_idx = 1
    from datetime import datetime

    while cur_start_day <= end_day:
        load_start_day = (datetime.strptime(cur_start_day, "%Y-%m-%d") - timedelta(days=cycle)).strftime("%Y-%m-%d")
        load_end_day = (datetime.strptime(cur_start_day, "%Y-%m-%d") - timedelta(days=0)).strftime("%Y-%m-%d")
        print(f'generate exchange month {month_idx} from {load_start_day} to {load_end_day}')

        # load online_data
        quote_vol_dict = load_data(load_start_day + ' 00:00:00', load_end_day + f' 23:00:00', 24 * cycle, 0)

        # rank coin by trade volumn
        rank_items = sorted(quote_vol_dict.items(), key=lambda d: d[1], reverse=True)
        rank_coins = [f'{item[0]} {item[1]}' for item in rank_items]

        file_utils.save_text(f'{base_dir}/data/pools/test.txt', rank_coins)
        exit()

        file_utils.save_text(f'{base_dir}/data/pools/exchange_month_cycle{cycle}days_{cur_start_day}.txt', rank_coins)

        cur_start_day = (datetime.strptime(start_day, "%Y-%m-%d") + relativedelta(months=+month_idx)).strftime("%Y-%m-%d")
        month_idx += 1

    pass

'''
    取每月前一周平均
'''
def rank_trade_amount_weekly():
    start_day = '2021-01-01'
    end_day='2021-08-30'
    cycle = 30
    cur_start_day = start_day

    idx = 1

    while cur_start_day <= end_day:

        load_start_day = (datetime.strptime(cur_start_day, "%Y-%m-%d") - timedelta(days=cycle)).strftime("%Y-%m-%d")
        load_end_day = (datetime.strptime(cur_start_day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        print(f'generate exchange week {idx} for {cur_start_day} from {load_start_day} to {load_end_day}')
        # load online_data
        quote_vol_dict = load_data(load_start_day + ' 00:00:00', load_end_day + f' 23:00:00', 24 * cycle, 7)

        # rank coin by trade volumn
        rank_items = sorted(quote_vol_dict.items(), key=lambda d: d[1], reverse=True)
        rank_coins = [item[0] for item in rank_items]

        file_utils.save_text(f'{base_dir}/data/pools/week/exchange_week_{cycle}days_{idx}.txt', rank_coins)

        cur_start_day = (datetime.strptime(start_day, "%Y-%m-%d") + relativedelta(weeks=+idx)).strftime("%Y-%m-%d")
        idx += 1

    pass

'''
    取每月前一周平均
'''
def rank_trade_amount_day():
    start_day = '2021-01-01'
    end_day='2021-08-30'
    cycle = 7
    cur_start_day = start_day

    idx = 1
    while cur_start_day <= end_day:

        load_start_day = (datetime.strptime(cur_start_day, "%Y-%m-%d") - timedelta(days=cycle)).strftime("%Y-%m-%d")
        load_end_day = (datetime.strptime(cur_start_day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        print(f'generate exchange {cur_start_day} from {load_start_day} to {load_end_day}')
        # load online_data
        quote_vol_dict = load_data(load_start_day + ' 00:00:00', load_end_day + f' 23:00:00', 24 * cycle, 7)

        # rank coin by trade volumn
        rank_items = sorted(quote_vol_dict.items(), key=lambda d: d[1], reverse=True)
        rank_coins = [item[0] for item in rank_items]

        file_utils.save_text(f'{base_dir}/data/pools/day/exchange_day_{cycle}days_{cur_start_day}.txt', rank_coins)

        cur_start_day = (datetime.strptime(start_day, "%Y-%m-%d") + relativedelta(days=+idx)).strftime("%Y-%m-%d")
        idx += 1
    pass


def rank_trade_amount_day2():
    start_day = '2021-01-01'
    end_day = '2021-09-01'
    cycle = 3
    from datetime import datetime
    load_start_day = (datetime.strptime(start_day, "%Y-%m-%d") - timedelta(days=cycle)).strftime("%Y-%m-%d")
    dt_vol_dict = cal_volumn_oneshot(load_start_day + ' 00:00:00', end_day + f' 23:00:00', cycle, 0)
    print(dt_vol_dict)
    sorted_dt_idx = list(dt_vol_dict.keys()).copy()
    sorted_dt_idx.sort()
    for idx in sorted_dt_idx:
        print(f'cal {idx} volumn rank')
        rank_items = sorted(dt_vol_dict[idx].items(), key=lambda d: d[1], reverse=True)
        rank_coins = [f'{item[0]}' for item in rank_items]
        file_utils.save_text(f'{base_dir}/data/pools/day/exchange_{cycle}days_{idx[0:10]}.txt', rank_coins)


def rank_trade_amount_month2():
    start_day = '2022-01-01'
    end_day = '2022-01-01'

    # 选pool用7天， rank用30天
    cycle = 30

    month_idx = 1
    dt_indexs = set()
    from datetime import datetime
    cur_start_day = start_day
    while cur_start_day <= end_day:
        dt_indexs.add(cur_start_day)
        cur_start_day = (datetime.strptime(start_day, "%Y-%m-%d") + relativedelta(months=+month_idx)).strftime("%Y-%m-%d")
        month_idx += 1

    load_start_day = (datetime.strptime(start_day, "%Y-%m-%d") - timedelta(days=cycle)).strftime("%Y-%m-%d")
    dt_vol_dict = cal_volumn_oneshot(load_start_day + ' 00:00:00', end_day + f' 23:00:00', cycle, 0, dt_indexs, shift=0)
    sorted_dt_idx = list(dt_vol_dict.keys()).copy()
    sorted_dt_idx.sort()
    for idx in sorted_dt_idx:
        print(f'cal {idx} volumn rank')
        rank_items = sorted(dt_vol_dict[idx].items(), key=lambda d: d[1], reverse=True)
        rank_coins = [f'{item[0]}' for item in rank_items]
        file_utils.save_text(f'{base_dir}/data/pools/month/exchange_{cycle}days_{idx[0:10]}.txt', rank_coins)

def rank_trade_amount_week2():
    start_day = '2021-01-01'
    end_day = '2021-09-02'

    cycle = 7

    month_idx = 1
    dt_indexs = set()
    from datetime import datetime
    cur_start_day = start_day
    while cur_start_day <= end_day:
        dt_indexs.add(cur_start_day)
        cur_start_day = (datetime.strptime(start_day, "%Y-%m-%d") + relativedelta(weeks=+month_idx)).strftime("%Y-%m-%d")
        month_idx += 1

    load_start_day = (datetime.strptime(start_day, "%Y-%m-%d") - timedelta(days=cycle)).strftime("%Y-%m-%d")
    dt_vol_dict = cal_volumn_oneshot(load_start_day + ' 00:00:00', end_day + f' 23:00:00', cycle, 0, dt_indexs, shift=1)
    sorted_dt_idx = list(dt_vol_dict.keys()).copy()
    sorted_dt_idx.sort()
    for idx in sorted_dt_idx:
        print(f'cal {idx} volumn rank')
        rank_items = sorted(dt_vol_dict[idx].items(), key=lambda d: d[1], reverse=True)
        rank_coins = [f'{item[0]}' for item in rank_items]
        file_utils.save_text(f'{base_dir}/data/pools/week/exchange_{cycle}days_{idx[0:10]}.txt', rank_coins)

def test():
    legal_set = set()

    with open('../data/debug/pool_test.txt', 'r') as f:
        idx = 0
        for line in f.readlines():
            coin = line.strip().lower()
            idx += 1
            legal_set.add(coin)

    with open('../data/exchange.txt', 'r') as f:
        for line in f.readlines():
            coin = line.strip().lower()
            if coin in legal_set:
                print(coin)

if __name__ == '__main__':
    rank_trade_amount_month2() #目前的baseline
    #rank_trade_amount_monthly()
    #rank_trade_amount_weekly()
    #rank_trade_amount_week2()
    #rank_trade_amount_day()
    #rank_trade_amount_day2()

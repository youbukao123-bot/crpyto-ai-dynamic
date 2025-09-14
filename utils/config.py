# -*- coding:utf-8 -*-

import json
import numpy as np
from utils.constants import *

class Config:
    def __init__(self):
        self.api_key: str = None
        self.api_secret: str = None
        self.top_n_coins = 100
        self.pct_days = 3
        self.one_buy_ratio = 0.8
        self.sell_pct_rank_min = 20
        self.top_k_mm_buy = 3
        self.zhisun_pct = DEFAULT_ZHISUN_PCT
        self.hours_cycle = 24  # 每N小时交易一次
        self.trade_time = 7  # 几点交易
        self.init_cash = 1_000_000
        self.proxy_host = ""  # proxy host
        self.proxy_port = 0  # proxy port
        self.buy_real = 0
        self.time_zone_diff = 0
        self.start_time = ""
        self.fetch_data_hours = 0
        self.zhiying_pct = -100
        self.btc_min_score = -100
        self.btc_max_score = 100
        self.last_pct_hour = 4
        self.last_pct_max = 0.1
        self.kline_dat_dir = ''
        self.MAX_LEGAL_RISE_RATIO = 0.5
        self.MAX_LEGAL_RISE_RATIO_ONEDAY = 0.5
        self.MAX_LEGAL_FALL_RATIO_ONEDAY = -100
        self.MAX_LEGAL_HIGH_RATIO = 100
        self.MIN_LEGAL_RISE_RATIO = -100
        self.MIN_VOLUMN_RATIO = -100
        self.MAX_N_DAY_PCT = 100
        self.top_k_mm_buy_shift = 0
        self.pool_cycle = 7

        #self.dynamic_zhiying_pcts = {'1-10':0.15, '11-20':0.3, '21-30':0.5, '31-50':1.0, '51-75':2.5, '76-100':3.5}
        self.dynamic_zhiying_pcts = {}
        self.dynamic_zhiying_pcts_matrics = list(np.zeros(300))

        self.dynamic_zhisun_pcts = {}
        #self.dynamic_zhisun_pcts = {'1-10':-0.1, '11-20':-0.15, '21-30':-0.2, '31-50':-0.3, '51-75':-0.5, '76-100':-100}
        self.dynamic_zhisun_pcts_matrics = list(np.zeros(300))


    def reload_params(self):
        self.dynamic_zhiying_pcts_matrics = list(np.zeros(300))
        for k, v in self.dynamic_zhiying_pcts.items():
            start, end = k.split('-')
            start = int(start)
            end = int(end)
            for i in range(start, end + 1):
                self.dynamic_zhiying_pcts_matrics[i] = v

        self.dynamic_zhisun_pcts_matrics = list(np.zeros(300))
        for k, v in self.dynamic_zhisun_pcts.items():
            start, end = k.split('-')
            start = int(start)
            end = int(end)
            for i in range(start, end + 1):
                self.dynamic_zhisun_pcts_matrics[i] = v


    def loads(self, config_file=None):
        """ Load config file.
        Args:
            config_file: config json file.
        """
        configures = {}
        if config_file:
            try:
                with open(config_file) as f:
                    data = f.read()
                    configures = json.loads(data)
            except Exception as e:
                print(e)
                exit(0)
            if not configures:
                print("config json file error!")
                exit(0)
        self._update(configures)

    def _update(self, update_fields):
        """
        更新update fields.
        :param update_fields:
        :return: None

        """
        for k, v in update_fields.items():
            setattr(self, k, v)

config = Config()
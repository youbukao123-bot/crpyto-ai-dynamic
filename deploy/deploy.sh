
cd ../
rm online_mm.zip
#zip  -r online_mm.zip online/ utils/  gateway/ online_data/
zip  -r online_mm.zip online/ utils/ gateway/ trade/ run_strategy_online.py


scp online_mm.zip  ubuntu@152.32.145.162:/home/ubuntu/trade_mm_1
scp online_mm.zip  ubuntu@152.32.145.162:/home/ubuntu/trade_mm_2
#scp online_mm.zip  ubuntu@152.32.145.162:/home/ubuntu/trade_mm_3

#scp online_mm.zip  ubuntu@152.32.144.246:/home/ubuntu/trade_mm_1

cd $1
cp ../trade_mm_2/deploy.sh .
cp ../trade_mm_2/run_strategy.sh .
mkdir log
mkdir -p online_data/config
cp ../trade_mm_2/online_data/config/config.json online_data/config/
mkdir -p online_data/hour
mkdir -p online_data/hist
mkdir -p online_data/log
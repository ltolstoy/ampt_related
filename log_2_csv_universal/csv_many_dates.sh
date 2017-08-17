#!/bin/bash
# Script to run /media/win_share/scripts/log_2_csv_universal/log_2_csv.sh for all blocks found in folder
# parameter is the path to the dir with log files: /media/win_EON_data_log/kee/150404/
# Run: csv_many_dates.sh /media/win_EON/data_log/xsol/
# It will change folders in range date (see i), and files in range 20xxxxxx(date)
#set -x
if [ $# -eq 0 ]
  then
  echo "No arguments supplied, can't run! Run it with argument like /media/win_EON/data_log/site_folder/"
fi
P="/media/win_share/scripts/log_2_csv_universal/log_2_csv.sh"
for i in {170701..170717};
do FN="20"$i
if [ -e $1/$i/$FN"_b1.log" ]
then
    $P $1/$i/$FN"_b1.log"
fi
if [ -e $1/$i/$FN"_b2.log" ]
then
    $P $1/$i/$FN"_b2.log"
fi
if [ -e $1/$i/$FN"_b3.log" ]
then
    $P $1/$i/$FN"_b3.log"
fi
if [ -e $1/$i/$FN"_b4.log" ]
then
    $P $1/$i/$FN"_b4.log"
fi
if [ -e $1/$i/$FN"_b5.log" ]
then
    $P $1/$i/$FN"_b5.log"
fi
if [ -e $1/$i/$FN"_b6.log" ]
then
    $P $1/$i/$FN"_b6.log"
fi
if [ -e $1/$i/$FN"_b7.log" ]
then
    $P $1/$i/$FN"_b7.log"
fi
#------------------
if [ -e $1/$i/$FN"_301.log" ]
then
    $P $1/$i/$FN"_301.log"
fi
if [ -e $1/$i/$FN"_302.log" ]
then
    $P $1/$i/$FN"_302.log"
fi
if [ -e $1/$i/$FN"_303.log" ]
then
    $P $1/$i/$FN"_303.log"
fi
if [ -e $1/$i/$FN"_304.log" ]
then
    $P $1/$i/$FN"_304.log"
fi
if [ -e $1/$i/$FN"_305.log" ]
then
    $P $1/$i/$FN"_305.log"
fi
if [ -e $1/$i/$FN"_306.log" ]
then
    $P $1/$i/$FN"_306.log"
fi
if [ -e $1/$i/$FN"_307.log" ]
then
    $P $1/$i/$FN"_307.log"
fi
if [ -e $1/$i/$FN"_308.log" ]
then
    $P $1/$i/$FN"_308.log"
fi
#------------
if [ -e $1/$i/$FN"_401.log" ]
then
    $P $1/$i/$FN"_401.log"
fi
if [ -e $1/$i/$FN"_402.log" ]
then
    $P $1/$i/$FN"_402.log"
fi
if [ -e $1/$i/$FN"_403.log" ]
then
    $P $1/$i/$FN"_403.log"
fi
if [ -e $1/$i/$FN"_404.log" ]
then
    $P $1/$i/$FN"_404.log"
fi
if [ -e $1/$i/$FN"_405.log" ]
then
    $P $1/$i/$FN"_405.log"
fi
if [ -e $1/$i/$FN"_406.log" ]
then
    $P $1/$i/$FN"_406.log"
fi
if [ -e $1/$i/$FN"_407.log" ]
then
    $P $1/$i/$FN"_407.log"
fi
if [ -e $1/$i/$FN"_408.log" ]
then
    $P $1/$i/$FN"_408.log"
fi
#---------------
if [ -e $1/$i/$FN"_501.log" ]
then
    $P $1/$i/$FN"_501.log"
fi
if [ -e $1/$i/$FN"_502.log" ]
then
    $P $1/$i/$FN"_502.log"
fi
if [ -e $1/$i/$FN"_503.log" ]
then
    $P $1/$i/$FN"_503.log"
fi
if [ -e $1/$i/$FN"_504.log" ]
then
    $P $1/$i/$FN"_504.log"
fi
if [ -e $1/$i/$FN"_505.log" ]
then
    $P $1/$i/$FN"_505.log"
fi
if [ -e $1/$i/$FN"_506.log" ]
then
    $P $1/$i/$FN"_506.log"
fi
if [ -e $1/$i/$FN"_507.log" ]
then
    $P $1/$i/$FN"_507.log"
fi
if [ -e $1/$i/$FN"_508.log" ]
then
    $P $1/$i/$FN"_508.log"
fi
#-----------
done
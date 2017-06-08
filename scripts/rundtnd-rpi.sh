hname=`hostname`
echo $hname

dtnd -i wlan0 -c ibrdtnd.conf.h$hname &


KEY="ebbf381a37944e3f92ede837445d7172"
ROLEID="8754258"
HOUR=08
MINUTE=00
PROCESS=32
FILE="pc_coupon.txt"
if [ -e $FILE ]; then
    rm -f $FILE
fi
echo "Login to JD ..."
python py/jd_coupon_pc.py -k $KEY -r $ROLEID -hh $HOUR -m $MINUTE -p $PROCESS -l $FILE
USER="jd_coupon_log"
PASS="jd123456"
TO="jd_coupon_log@163.com"
if [ -e $FILE ]; then
    echo "Send email to $TO ..."
    python py/email163.py -u $USER -p $PASS -t $TO -f $FILE
fi

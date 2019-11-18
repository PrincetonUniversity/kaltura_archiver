#/bin/tcsh 

source nogit/prod.rc 

set KALTURA_SESSION=`curl -X POST "https://www.kaltura.com/api_v3/service/session/action/start" \
    -d "secret=$KALTURA_SECRET" \
    -d "userId=$KALTURA_USERID" \
    -d "type=0" \
    -d "partnerId=$KALTURA_PARTNERID" \
    -d "expiry=86400" \
    -d "format=1" | sed 's@"@@g'`

echo "setenv KALTURA_SESSION $KALTURA_SESSION"


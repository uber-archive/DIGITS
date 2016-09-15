#!/usr/bin sh

export ORIGIN=$(dirname $(dirname $(which python)))
export DIGITS_HOME=$ORIGIN/digits
export DATA_DIR=/mnt/data/digits
export PATH=$DIGITS_HOME:$PATH

if [ ! -d "$DATA_DIR" ]; then
  mkdir $DATA_DIR
fi

if [ ! -d "$DATA_DIR/jobs" ]; then
  mkdir $DATA_DIR/jobs
fi

if [ ! -d "$DATA_DIR/static" ]; then
  mkdir $DATA_DIR/static
  cp -r $DIGITS_HOME/digits/static/* $DATA_DIR/static/.
fi

cp $DIGITS_HOME/conda/* $DATA_DIR/.
sed -i "s+DIGIT_HOME_PLACE_HOLDER+$DIGITS_HOME+" $DATA_DIR/digits.site
sed -i "s+DIGIT_DATA_PLACE_HOLDER+$DATA_DIR+" $DATA_DIR/digits.site



if [ ! -d "/etc/nginx/sites-enabled" ]; then
 echo "fix the installation of digits by executing commands below once"
 echo "sudo mkdir /etc/nginx/sites-enabled"
fi

if [ ! -f "/etc/nginx/sites-enabled/digits.site" ]; then
 echo "sudo cp "$DATA_DIR"/digits.site /etc/nginx/sites-enabled/."
fi

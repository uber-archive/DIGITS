#!/usr/bin sh

export ORIGIN=$(dirname $(dirname $(which python)))
export DIGITS_HOME=$ORIGIN/digits
export DATA_DIR=/mnt/data/digits
export PATH=$DIGITS_HOME:$PATH

if [ ! -d "$DATA_DIR" ]; then
  mkdir $DATA_DIR
end

if [ ! -d "$DATA_DIR/jobs" ]; then
  mkdir $DATA_DIR/jobs
end

if [ ! -d "$DATA_DIR/static" ]; then
  mkdir $DATA_DIR/static
  cp -r $DIGITS_HOME/digits/static/* $DATA_DIR/static/.
end

cp $DIGITS_HOME/conda/digits.site $DATA_DIR/.
sed -i 's+DIGIT_HOME_PLACE_HOLDER+${DIGITS_HOME}+' $DATA_DIR/digits.site
sed -i 's+DIGIT_DATA_PLACE_HOLDER+${DATA_DIR}+' $DATA_DIR/digits.site

echo execute the following steps
echo sudo mkdir /etc/nginx/ && mkdir /etc/nginx/sites-enabled/ && cp $DATA_DIR/digits.site /etc/nginx/sites-enabled/


#!/usr/bin sh

export ORIGIN=$(dirname $(dirname $(which python)))
export DIGITS_HOME=$ORIGIN/digits
export DATA_DIR=/mnt/data/digits
export PATH=$DIGITS_HOME:$PATH

if [ ! -d "$DATA_DIR" ]; then
  mkdir $DATA_DIR
end

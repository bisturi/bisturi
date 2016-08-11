#PYTHON="coverage run --branch -p" # or python
PYTHON="python"

pushd .
cd bisturi

for t in ../docs/reference/$1*.md
do
   if [ -e $t ]
   then
      echo $t
      $PYTHON -m doctest $t
   fi
done

for t in ../examples/$1*.py
do
   if [ -e $t ]
   then
      echo $t
      $PYTHON $t
   fi
done

popd

pushd .
cd tests

for t in test_$1*.py
do
   if [ -e $t ]
   then
      echo $t
      $PYTHON -m unittest -q "${t%%.*}"
   fi
done

popd

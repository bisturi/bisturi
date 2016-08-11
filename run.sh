pushd .
cd bisturi

for t in ../docs/reference/$1*.rst
do
   if [ -e $t ]
   then
      echo $t
      python -m doctest $t
   fi
done

for t in ../examples/$1*.py
do
   if [ -e $t ]
   then
      echo $t
      python $t
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
      python -m unittest -q "${t%%.*}"
   fi
done

popd

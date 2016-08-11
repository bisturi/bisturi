pushd .
cd bisturi

for t in ../docs/reference/*.rst
do
   echo $t
   python -m doctest $t
done

for t in ../examples/*.py
do
   echo $t
   python $t
done

popd

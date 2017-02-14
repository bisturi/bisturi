#PYTHON="coverage run --branch -p" # or python
PYTHON="python"

pushd() {
    command pushd "$@" > /dev/null
}

popd() {
    command popd "$@" > /dev/null
}

FILTER=""
case "$1" in
    DOC*)
        CAT="DOCS"
        ;;
    CODE*)
        CAT="CODE"
        ;;
    TEST*)
        CAT="TESTS"
        ;;
    EXAMPLE*)
        CAT="EXAMPLES"
        ;;
    MISC*)
        CAT="MISC"
        ;;
    *)
        CAT="ALL"
        FILTER="$1"
        ;;
esac

if [ "$CAT" = "ALL" -o "$CAT" = "DOCS" ]
then
for t in docs/reference/$FILTER*.md
do
   if [ -e $t ]
   then
      echo $t
      $PYTHON -m doctest $t
   fi
done
fi

if [ "$CAT" = "ALL" -o "$CAT" = "MISC" ]
then
for t in docs/tutorial_by_example/$FILTER*.md
do
   if [ -e $t ]
   then
      echo $t
      $PYTHON -m doctest $t
   fi
done
fi

if [ "$CAT" = "ALL" -o "$CAT" = "CODE" ]
then
for t in bisturi/$FILTER*.py
do
   if [ -e $t ]
   then
      echo $t
      $PYTHON -m doctest $t
   fi
done
fi

if [ "$CAT" = "ALL" -o "$CAT" = "MISC" ]
then
for t in $FILTER*.md
do
   if [ -e $t ]
   then
      echo $t
      $PYTHON -m doctest $t
   fi
done
fi


pushd .
cd bisturi

if [ "$CAT" = "ALL" -o "$CAT" = "EXAMPLES" ]
then
for t in ../examples/$FILTER*.py
do
   if [ -e $t ]
   then
      echo $t
      $PYTHON $t
   fi
done
fi

popd

pushd .
cd tests

if [ "$CAT" = "ALL" -o "$CAT" = "TESTS" ]
then
for t in test_$FILTER*.py
do
   if [ -e $t ]
   then
      echo $t
      $PYTHON -m unittest -q "${t%%.*}"
   fi
done
fi

popd

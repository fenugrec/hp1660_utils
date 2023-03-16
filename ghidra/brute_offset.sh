#!/bin/bash

# example:
# sh brute_offset.sh ./trash test.bin 68000:BE:32:MC68020

GHIDRA_PROJECTS=$1
FILENAME=$2
LANGID=$3
BASE_ADDR=$4
TMP_PROJECT_NAME=$RANDOM
#CMD="$GHIDRA_HOME/support/analyzeHeadless \"$GHIDRA_PROJECTS\" \"$TMP_PROJECT_NAME\" -import \"$FILENAME\" -postScript CountReferencedStrings.java -processor \"$LANGID\" -deleteProject -loader BinaryLoader -loader-baseAddr \"$BASE_ADDR\" -loader-fileOffset"
CMD="ghidra-analyzeHeadless \"$GHIDRA_PROJECTS\" \"$TMP_PROJECT_NAME\" -import \"$FILENAME\" -postScript CountReferencedStrings.java -processor \"$LANGID\" -deleteProject -loader BinaryLoader -loader-baseAddr "

COUNTER=0
#for i in {0..128}
for i in 0 0x100000 0x400000 0x800000
do
        echo "-----" >> analysis.log
        printf $i >> analysis.log
        $CMD $i 2>&1 | grep "CountReferencedStrings.java>" >> analysis.log
        #echo $CMD $i
        echo "-----" >> analysis.log
        COUNTER=$((COUNTER+4))
done

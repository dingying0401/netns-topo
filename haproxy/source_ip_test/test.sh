#!/bin/bash

for c in client1 client2 client3; do
    for s in 20.0.0.2 20.0.0.3; do
        echo "=============== Now curl $s from $c ====================="
        ip netns exec $c sh -c "for i in {1..10} ; do curl -sS $s; done"
        echo ""
    done
done

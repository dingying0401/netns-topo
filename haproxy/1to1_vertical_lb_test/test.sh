#!/bin/bash

for c in client1 client2 client3; do
    echo "=============== Now curl outer-lb 20.0.0.3 from $c ====================="
    ip netns exec $c sh -c "for i in {1..10} ; do curl -sS 20.0.0.3; done"
    echo ""
done

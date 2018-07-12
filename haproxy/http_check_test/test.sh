#!/bin/bash

echo "Now curl 10.0.0.2 from client, no response from node3 should be seen"
ip netns exec client sh -c "for i in {1..10} ; do curl -sS 10.0.0.2; done"

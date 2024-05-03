# tr-partial-descriptors-test

Just experimenting with taproot descriptors and Bitcoin-core.  
The tests use a custom version of bitcoind built from [wip-tr-raw-nodes](https://github.com/Eunovo/bitcoin/tree/wip-tr-raw-nodes)

## How to run
`python3 src/main.py <path_to_bitcoind> <rpcport_to_use>`
The script will start the provided bitcoind binary on the provided port, run tests against it and shut it down.

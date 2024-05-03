from secp256k1 import *
import bip32
from jsonrpcproxy import *
import sys
import subprocess
import tempfile
import time

def get_key_pair(index, seed=b'deadbeef', derivation='m/0h'):

    master = bip32.BIP32.from_seed(seed)
    d = ECKey().set(master.get_privkey_from_path(f'{derivation}/{index}'))
    P = d.get_pubkey()

    return d, P

### Test that the specified branch in tree can be spent even though rawnode is used to omit a branch ###
def rawnode_test(proxy: JsonRpcProxy, internal_key: tuple[ECKey, ECPubKey]):
  print("Starting rawnode_test...")
  bip32_seed = "1a2b3c4d"
  (key, pubkey) = get_key_pair(0, seed=bytes.fromhex(bip32_seed))
  rawnode = "rawnode(e960f9fcfb646b5a6eb3a091d9270497738f7bcd99c2dda549acc699f02b043b)"

  for (i, key_str) in enumerate([key.get_bytes().hex(), pubkey.get_bytes(True).hex()]):
    leaf_script = "pk(%s)" % key_str
    descriptor = "tr(%s,{%s,%s})" % (internal_key[1].get_bytes().hex(), rawnode, leaf_script)
    walletname = "rawnodewallet_%i" % i

    print("Creating wallet with descriptor: ", descriptor)
    proxy.send("createwallet", [walletname, False, True, "", True])
    proxy = proxy.proxy("/wallet/"+walletname)
    proxy.send("importdescriptors", [[{"desc": descriptor, "active": True, "timestamp": "now", "internal": False}]])

    # Test spending

    print("Generating funds to wallet address...")
    address = proxy.send("getnewaddress", ["", "bech32m"])
    proxy.send("generatetoaddress", [101, address])
    
    print("Sending funds to another address...")
    address2 = proxy.send("getnewaddress", ["", "bech32m"])
    txid = proxy.send("sendtoaddress", {"address": address2, "amount": 1.0, "subtractfeefromamount": False, "fee_rate": 25})
    print("Txid: "+txid)

    result = proxy.send("gettransaction", {"txid": txid, "verbose": True})

    print(json.dumps(result['details'], indent=4))
    print(json.dumps(result['decoded'], indent=4))

    # proxy.send("sendrawtransaction", [result['hex']])

  print("rawnode_test pased!")

if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: python main.py <path_to_bitcoind> <rpcport>")
    sys.exit(1)
  path_to_bitcoind = sys.argv[1]
  rpcport = sys.argv[2]
  rpcuser = "tester"
  rpcpassword = "password"

  # Run the bitcoind binary
  with tempfile.TemporaryDirectory() as tmpdir:
    print("Using tmp dir: "+tmpdir)
    bitcoind = subprocess.Popen([path_to_bitcoind, "-datadir=%s" % tmpdir, "-regtest", "-daemon", "-rpcport=%s" % rpcport, "-rpcuser=%s" % rpcuser, "-rpcpassword=%s" % rpcpassword])
    try:
      # Wait for bitcoind to start
      time.sleep(5)

      proxy = JsonRpcProxy("http://" + rpcuser + ":" + rpcpassword + "@127.0.0.1:" + rpcport, rpcuser, rpcpassword)

      # Test bitcoin rpc connection
      proxy.send("getblockchaininfo", [])

      bip32_seed = "deadbeef"
      internal_key = get_key_pair(0, seed=bytes.fromhex(bip32_seed))

      rawnode_test(proxy, internal_key)
    finally:
      bitcoind.terminate()
      bitcoind.wait()

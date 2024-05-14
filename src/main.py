from secp256k1 import *
import bip32
from jsonrpcproxy import *
import sys
import subprocess
import tempfile
import time

def get_key_pair(index, seed=b'deadbeef', derivation='m/0h'):

    master = bip32.BIP32.from_seed(seed, network="test")
    d = ECKey().set(master.get_privkey_from_path(f'{derivation}/{index}'))
    P = d.get_pubkey()

    return d, P

def test_rawnode_wallet_generate_same_address(proxy: JsonRpcProxy, internal_keys: tuple[ECKey, ECPubKey]):
  print("Test Rawnode wallet generate same address")

  bip32_ = bip32.BIP32.from_seed(b'1ab2b3c4d', network="test")

  internal_key = internal_keys[1].get_bytes(True).hex()
  partner_1_key = bip32_.get_xpriv_from_path("m/2h") + "/*"
  partner_1_pub = bip32_.get_xpub_from_path("m/2h") + "/*"
  partner_2_key = ECPubKey().set(bip32_.get_pubkey_from_path("m/3h")).get_bytes(True).hex()
  partner_3_key = ECPubKey().set(bip32_.get_pubkey_from_path("m/4h")).get_bytes(True).hex()
  lawyer_key = ECPubKey().set(bip32_.get_pubkey_from_path("m/5h")).get_bytes(True).hex()

  two_partner_script = "multi_a(2,%s,%s,%s)" % (partner_1_key, partner_2_key, partner_3_key)
  lawyer_and_partner_1_script = "and_v(v:older(4320),multi_a(2,%s,%s))" % (lawyer_key, partner_1_pub)
  lawyer_and_partner_2_script = "and_v(v:older(4320),multi_a(2,%s,%s))" % (lawyer_key, partner_2_key)
  lawyer_and_partner_3_script = "and_v(v:older(4320),multi_a(2,%s,%s))" % (lawyer_key, partner_3_key)
  lawyer_only_script = "and_v(v:older(12960),pk(%s))" % lawyer_key

  rawnode = "rawnode(8a62dc0a100c4156cc2a4b7c2a97747ce0dfe90562673fd662678aaae93121fb)"
  
  descriptor1 = "tr(%s,{%s,{{%s,%s},{%s,%s}}})" % (internal_key, two_partner_script, lawyer_and_partner_1_script, lawyer_and_partner_2_script, lawyer_and_partner_3_script, lawyer_only_script)
  descriptor2 = "tr(%s,{%s,%s})" % (internal_key, two_partner_script, rawnode)
 
  addresses = []
  for (walletname, descriptor) in [("complex_desc1", descriptor1), ("complex_desc2", descriptor2)]:
    descriptor += "#" + proxy.send("getdescriptorinfo", [descriptor])['checksum']
    print("Creating wallet %s with descriptor: \r\n%s" % (walletname, descriptor))
  
    proxy.send("createwallet", [walletname, False, True, "", True])
    proxy = proxy.proxy("/wallet/"+walletname)
    proxy.send("importdescriptors", [[{"desc": descriptor, "active": True, "timestamp": "now", "internal": False}]])
    address = proxy.send("getnewaddress", ["", "bech32m"])
    addresses.append(address)

    print("Generated address: %s for wallet: %s" % (address, walletname))

  print("Check that all wallets generated the same address")
  for (i, addr) in enumerate(addresses):
    if (i == len(addresses) - 1):
      break
    assert(addr == addresses[i+1])

  print("Test passed successfully!")

### Test that the specified branch in tree can be spent even though rawnode is used to omit a branch ###
def test_specified_branch_can_be_used(proxy: JsonRpcProxy, internal_key: tuple[ECKey, ECPubKey]):
  print("Starting rawnode_test...")
  
  bip32_ = bip32.BIP32.from_seed(b'1ab2b3c4d', network="test")
  xpriv = bip32_.get_xpriv_from_path("m/2h") + "/*"
  xpub = bip32_.get_xpub_from_path("m/3h") + "/*"
  
  rawnode = "rawnode(e960f9fcfb646b5a6eb3a091d9270497738f7bcd99c2dda549acc699f02b043b)"

  for (i, key_str) in enumerate([xpub]):
    leaf_script = "pk(%s)" % key_str
    descriptor = "tr(%s,{%s,%s})" % (internal_key[1].get_bytes(True).hex(), rawnode, leaf_script)
    descriptor += "#" + proxy.send("getdescriptorinfo", [descriptor])['checksum']
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

  print("Test pased!")

if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: python main.py <path_to_bitcoind> <rpcport>")
    sys.exit(1)
  path_to_bitcoind = sys.argv[1]
  rpcport = sys.argv[2]
  rpcuser = "tester"
  rpcpassword = "password"
  start_bitcoind = True

  # Run the bitcoind binary
  with tempfile.TemporaryDirectory() as tmpdir:
    print("Using tmp dir: "+tmpdir)
    bitcoind = None
    if start_bitcoind == True:
      bitcoind = subprocess.Popen([path_to_bitcoind, "-datadir=%s" % tmpdir, "-regtest", "-daemon", "-rpcport=%s" % rpcport, "-rpcuser=%s" % rpcuser, "-rpcpassword=%s" % rpcpassword])
    try:
      # Wait for bitcoind to start
      time.sleep(5)

      proxy = JsonRpcProxy("http://" + rpcuser + ":" + rpcpassword + "@127.0.0.1:" + rpcport, rpcuser, rpcpassword)

      # Test bitcoin rpc connection
      proxy.send("getblockchaininfo", [])

      bip32_seed = "deadbeef"
      internal_key = get_key_pair(0, seed=bytes.fromhex(bip32_seed))

      # test_specified_branch_can_be_used(proxy, internal_key)
      test_rawnode_wallet_generate_same_address(proxy, internal_key)
    finally:
      if bitcoind is not None:
        bitcoind.terminate()
        bitcoind.wait()

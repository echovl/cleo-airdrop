import os

from web3 import Web3, contract


def get_potential_holders(w3: Web3, venft: contract.Contract) -> [str]:
    genesis_block = 69820005
    latest_block = w3.eth.block_number

    venft_depositors = []
    current_block = genesis_block
    block_step = 5000000

    while current_block < latest_block:
        from_block = current_block
        to_block = from_block + block_step

        if to_block > latest_block:
            to_block = latest_block

        event_filter = venft.events.Deposit.create_filter(
            fromBlock=from_block, toBlock=to_block
        )

        events = event_filter.get_new_entries()
        venft_depositors += map(lambda e: e.args.provider, events)
        current_block = to_block + 1

    return list(set(venft_depositors))


rpc_url = os.environ.get("RPC_URL")

if rpc_url == None:
    print("missing RPC_URL environment variable")
    exit(1)

w3 = Web3(Web3.HTTPProvider(rpc_url))

with open("./abi//veNFT.json") as abi:
    venft_abi = abi.read()

venft = w3.eth.contract(
    address="0xAAA343032aA79eE9a6897Dab03bef967c3289a06", abi=venft_abi
)

depositors = get_potential_holders(w3, venft)

print(len(depositors))

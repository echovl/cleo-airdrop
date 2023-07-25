import os
from typing import List

from multicall import Call, Multicall
from web3 import Web3, contract

VERAM_LOCKED_ABI = "locked(uint256)(uint256,uint256)"
VERAM_OWNEROF_ABI = "ownerOf(uint256)(address)"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
MIN_LOCKED_AMOUNT = 100_000 * 1e18


class VeToken:
    def __init__(
        self, token_id: int, owner: str, locked_amount: int, lock_end: int
    ) -> None:
        self.token_id = token_id
        self.owner = owner
        self.locked_amount = locked_amount
        self.lock_end = lock_end


def batch_multicall(calls: List[Call], batch_size: int):
    step = int(len(calls) / batch_size)

    output = {}
    for i in range(0, len(calls), step):
        print(f"chunk {i}")
        res = Multicall(calls[i : i + step])()
        output = {**output, **res}

    return output


def get_eligible_tokens(w3: Web3, venft: contract.Contract) -> List[VeToken]:
    max_token_id = venft.functions.tokenId().call()

    os.environ["AIOHTTP_TIMEOUT"] = "300"

    token_ids = range(max_token_id)

    locked_calls = [
        Call(
            venft.address,
            [VERAM_LOCKED_ABI, id],
            [(str(id) + "_amount", None), (str(id) + "_end", None)],
        )
        for id in token_ids
    ]

    ownerof_calls = [
        Call(venft.address, [VERAM_OWNEROF_ABI, id], [(str(id), None)])
        for id in token_ids
    ]

    locked = batch_multicall(locked_calls, 30)
    ownerof = batch_multicall(ownerof_calls, 30)

    ve_tokens: List[VeToken] = []

    for token_id in token_ids:
        owner: str = ownerof.get(str(token_id))
        locked_amount: int = locked.get(str(token_id) + "_amount")
        lock_end: int = locked.get(str(token_id) + "_end")

        if owner == None and owner != ZERO_ADDRESS:
            continue

        if locked_amount == None:
            continue

        if locked_amount < MIN_LOCKED_AMOUNT:
            continue

        if owner.lower() == "0xcba1a275e2d858ecffaf7a87f606f74b719a8a93":
            print(token_id, locked_amount, lock_end)

        ve_tokens.append(VeToken(token_id, owner.lower(), locked_amount, lock_end))

    return ve_tokens


rpc_url = os.environ.get("RPC_URL")

if rpc_url == None:
    print("missing RPC_URL environment variable")
    exit(1)

w3 = Web3(Web3.HTTPProvider(rpc_url))

with open("./abi/veNFT.json") as abi:
    venft_abi = abi.read()

venft = w3.eth.contract(
    address="0xAAA343032aA79eE9a6897Dab03bef967c3289a06", abi=venft_abi
)

tokens = get_eligible_tokens(w3, venft)

print(len(tokens))

import csv
import os
import time
from typing import List

from multicall import Call, Multicall
from web3 import Web3

import constants


class VeToken:
    def __init__(
        self,
        token_id: int,
        owner: str,
        locked_amount: int,
        lock_end: int,
        airdrop_amount: int = 0,
    ) -> None:
        self.token_id = token_id
        self.owner = owner
        self.locked_amount = locked_amount
        self.lock_end = lock_end
        self.airdrop_amount = airdrop_amount


def from_wei(value) -> int:
    return value / 1e18


def batch_multicall(w3: Web3, calls: List[Call], batch_size: int):
    step = int(len(calls) / batch_size)

    output = {}
    for i in range(0, len(calls), step):
        print(f"chunk {i}")
        res = Multicall(calls[i : i + step], _w3=w3)()
        output = {**output, **res}

    return output


def get_eligible_tokens(w3: Web3) -> List[VeToken]:
    max_token_id = Call(constants.VERAM_ADDRESS, [constants.VERAM_TOKEN_ID], _w3=w3)()

    print(max_token_id)

    timestamp = time.time()
    os.environ["AIOHTTP_TIMEOUT"] = "300"

    token_ids = [
        id for id in range(max_token_id) if id not in constants.BLACKLISTED_NFTS
    ]

    locked_calls = [
        Call(
            constants.VERAM_ADDRESS,
            [constants.VERAM_LOCKED_ABI, id],
            [(str(id) + "_amount", from_wei), (str(id) + "_end", None)],
        )
        for id in token_ids
    ]

    ownerof_calls = [
        Call(
            constants.VERAM_ADDRESS,
            [constants.VERAM_OWNEROF_ABI, id],
            [(str(id), None)],
        )
        for id in token_ids
    ]

    locked = batch_multicall(w3, locked_calls, 10)
    ownerof = batch_multicall(w3, ownerof_calls, 10)

    ve_tokens: List[VeToken] = []

    for token_id in token_ids:
        owner: str = ownerof.get(str(token_id))
        locked_amount: int = locked.get(str(token_id) + "_amount")
        lock_end: int = locked.get(str(token_id) + "_end")
        locked_time = lock_end - timestamp

        if owner == None or owner == constants.ZERO_ADDRESS:
            continue

        if locked_amount == None or locked_amount < constants.MIN_LOCKED_AMOUNT:
            continue

        if locked_amount < constants.MIN_LOCKED_AMOUNT:
            continue

        if locked_time < constants.THREE_AND_HALF_YEARS_IN_SECONDS:
            continue

        ve_tokens.append(VeToken(token_id, owner.lower(), locked_amount, lock_end))

    total_ve = sum(token.locked_amount for token in ve_tokens)
    for token in ve_tokens:
        token.airdrop_amount = (
            constants.AIRDROP_ALLOCATION * token.locked_amount / total_ve
        )

    assert constants.AIRDROP_ALLOCATION == sum(
        token.airdrop_amount for token in ve_tokens
    ), f"Calculated airdrop total amount must equal {constants.AIRDROP_ALLOCATION}"

    return ve_tokens


def take_snapshot():
    rpc_url = os.environ.get("RPC_URL")
    if rpc_url == None:
        rpc_url = "https://arb1.arbitrum.io/rpc"

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    tokens = get_eligible_tokens(w3)
    tokens = sorted(tokens, key=lambda t: t.locked_amount, reverse=True)

    with open("airdrop.csv", "w", newline="") as csvfile:
        fieldnames = ["token_id", "owner", "balance", "allocation"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()

        for tk in tokens:
            writer.writerow(
                {
                    "token_id": tk.token_id,
                    "owner": tk.owner,
                    "balance": tk.locked_amount,
                    "allocation": tk.airdrop_amount,
                }
            )


take_snapshot()

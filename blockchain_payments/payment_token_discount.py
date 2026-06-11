# blockchain_payments/payment_token_discount.py

from web3 import Web3
from dotenv import load_dotenv
import os
import json

load_dotenv()

POLYGON_RPC_URL = os.getenv("POLYGON_MAINNET_RPC_URL")
TOKEN_CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")  # Тут адреса SimpleToken
TOKEN_ABI_PATH = os.path.join(os.path.dirname(__file__), "contracts", "abi.json")

w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))


def load_token_abi():
    with open(TOKEN_ABI_PATH, "r") as f:
        return json.load(f)


def get_token_balance(user_address):
    abi = load_token_abi()
    contract = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_CONTRACT_ADDRESS), abi=abi)
    balance = contract.functions.balanceOf(Web3.to_checksum_address(user_address)).call()
    return balance


def calculate_discount(balance):
    if balance >= 100000:
        return 50
    elif balance >= 50000:
        return 25
    elif balance >= 10000:
        return 10
    elif balance >= 1000:
        return 5
    elif balance >= 100:
        return 1
    else:
        return 0


def get_user_discount(user_address):
    """
    Повертає знижку для користувача за токеном.
    Підказка: чим більше токенів на балансі, тим більша знижка.
    Пороги:
        100 000+ токенів — 50%
        50 000+ токенів — 25%
        10 000+ токенів — 10%
        1 000+ токенів — 5%
        100+ токенів — 1%
        менше 100 — 0%
    """
    balance = get_token_balance(user_address)
    discount = calculate_discount(balance)
    return discount


if __name__ == "__main__":
    # Приклад для перевірки
    user = input("Введіть адресу користувача: ")
    discount = get_user_discount(user)
    print(f"Знижка для {user}: {discount}%")

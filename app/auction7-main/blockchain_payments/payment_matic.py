# === [auction/payments/matic_payment.py] ===

from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv()

# Налаштування
RPC_URL = os.getenv("POLYGON_MAINNET_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT_ADDRESS = Web3.to_checksum_address(os.getenv("ACCOUNT_ADDRESS"))
TOKEN_CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS"))
ESCROW_ADDRESS = Web3.to_checksum_address(os.getenv("ESCROW_ADDRESS"))
ESCROW_PRIVATE_KEY = os.getenv("ESCROW_PRIVATE_KEY")
ADMIN_ADDRESS = Web3.to_checksum_address(os.getenv("ADMIN_ADDRESS"))
TOKEN_ABI_PATH = os.path.join(os.path.dirname(__file__), "contracts", "abi.json")

w3 = Web3(Web3.HTTPProvider(RPC_URL))

with open(TOKEN_ABI_PATH, "r") as f:
    import json
    abi = json.load(f)

token_contract = w3.eth.contract(address=TOKEN_CONTRACT_ADDRESS, abi=abi)

def check_discount(address):
    return token_contract.functions.getDiscount(address).call()

def send_payment(user_address, amount_matic):
    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    tx = {
        'nonce': nonce,
        'to': Web3.to_checksum_address(user_address),
        'value': w3.to_wei(amount_matic, 'ether'),
        'gas': 21000,
        'gasPrice': w3.to_wei('50', 'gwei')
    }

    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()

def send_to_escrow(from_private_key, from_address, amount_matic):
    nonce = w3.eth.get_transaction_count(from_address)
    tx = {
        'nonce': nonce,
        'to': ESCROW_ADDRESS,
        'value': w3.to_wei(amount_matic, 'ether'),
        'gas': 21000,
        'gasPrice': w3.to_wei('50', 'gwei')
    }
    signed_tx = w3.eth.account.sign_transaction(tx, from_private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()

def release_from_escrow(to_address, amount_matic):
    nonce = w3.eth.get_transaction_count(ESCROW_ADDRESS)
    tx = {
        'nonce': nonce,
        'to': Web3.to_checksum_address(to_address),
        'value': w3.to_wei(amount_matic, 'ether'),
        'gas': 21000,
        'gasPrice': w3.to_wei('50', 'gwei')
    }
    signed_tx = w3.eth.account.sign_transaction(tx, ESCROW_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()

def send_to_admin(from_private_key, from_address, amount_matic):
    nonce = w3.eth.get_transaction_count(from_address)
    tx = {
        'nonce': nonce,
        'to': ADMIN_ADDRESS,
        'value': w3.to_wei(amount_matic, 'ether'),
        'gas': 21000,
        'gasPrice': w3.to_wei('50', 'gwei')
    }
    signed_tx = w3.eth.account.sign_transaction(tx, from_private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()

def process_payment(user_wallet, order_amount):
    discount_percent = check_discount(user_wallet)
    discount_amount = order_amount * (discount_percent / 100)
    final_amount = order_amount - discount_amount

    tx_hash = send_payment(user_wallet, final_amount)
    return {
        "tx_hash": tx_hash,
        "final_amount": final_amount,
        "discount_percent": discount_percent
    }

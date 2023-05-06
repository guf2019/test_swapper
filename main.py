from web3 import Web3
from eth_account import Account
import requests
import os
from dotenv import load_dotenv


dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

public_key = os.environ.get("PUBLIC_KEY")
private_key = os.environ.get("PRIVATE_KEY")
provider = os.environ.get("PROVIDER")

w3 = Web3(Web3.HTTPProvider(provider))
Account.enable_unaudited_hdwallet_features()


# Define token addresses
TOKEN_ADDRESSES = {
    'ETH': '0x0000000000000000000000000000000000000000',
    'WETH': '0xB4FBF271143F4FBf7B91A5ded31805e42b2208d6',
    'UNI': '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'
}

ABIS = {
    'WETH': '',
    'UNI': '',
    'UNISWAP_ROUTER': '',
    'UNISWAP_FACTORY': ''
}

with open('./abi/uni.abi', 'r') as abi:
    ABIS['UNI'] = abi.readline()

with open('./abi/weth.abi', 'r') as abi:
    ABIS['WETH'] = abi.readline()

with open('./abi/uniswap_factory.abi', 'r') as abi:
    ABIS['UNISWAP_FACTORY'] = abi.readline()

with open('./abi/uniswap_router.abi', 'r') as abi:
    ABIS['UNISWAP_ROUTER'] = abi.readline()

def generate_account(mnemonic_phrase=True):
    if mnemonic_phrase:
        account, mnemonic = Account.create_with_mnemonic()
        return {
            'mnemonic_phrase': mnemonic,
            'private_key': account.key.hex(),
            'address': account.address
        }
    else:
        account = Account.create()
        return {
            'private_key': account.key.hex(),
            'address': account.address
        }


def swap_token(from_token, to_token, amount):
    from_token_address = w3.to_checksum_address(TOKEN_ADDRESSES[from_token])
    to_token_address = w3.to_checksum_address(TOKEN_ADDRESSES[to_token])
    factory_abi = ABIS["UNISWAP_FACTORY"]
    router_abi = ABIS["UNISWAP_ROUTER"]
    erc20_abi = ABIS["WETH"]

    factory_address = w3.to_checksum_address('0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f')
    router_address = w3.to_checksum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')

    # Create contract objects for the Uniswap factory and router contracts
    factory_contract = w3.eth.contract(address=factory_address, abi=factory_abi)
    router_contract = w3.eth.contract(address=router_address, abi=router_abi)

    pair_address = factory_contract.functions.getPair(TOKEN_ADDRESSES[from_token], TOKEN_ADDRESSES[to_token]).call()

    # Check if the pair exists
    if pair_address == '0x0000000000000000000000000000000000000000':
        raise Exception('Pair does not exist')


    nonce = w3.eth.get_transaction_count(w3.to_checksum_address(public_key))
    tx = w3.eth.contract(address=pair_address, abi=erc20_abi).functions.approve(
        router_address,
        amount).build_transaction({
            'gas': 70000,
            'gasPrice': w3.to_wei(5, 'gwei'),
            'nonce': nonce,
        })

    # Sign and send transaction
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    deadline = w3.eth.get_block('latest')['timestamp'] + 60

    nonce = w3.eth.get_transaction_count(w3.to_checksum_address(public_key))
    tx_hash = ''
    if from_token == 'ETH':
        tx_hash = router_contract.functions.swapExactETHForTokens(
            amount,
            [w3.to_checksum_address(TOKEN_ADDRESSES[from_token]), w3.to_checksum_address(TOKEN_ADDRESSES[to_token])],
            public_key,
            deadline
        ).build_transaction({
            'gas': 3000000,
            'gasPrice': w3.to_wei(5, 'gwei'),
            'nonce': nonce,
        })
    else:
        tx_hash = router_contract.functions.swapExactTokensForTokens(
            amount,
            0,
            [w3.to_checksum_address(TOKEN_ADDRESSES[from_token]), w3.to_checksum_address(TOKEN_ADDRESSES[to_token])],
            public_key,
            deadline
        ).build_transaction({
                'gas': 3000000,
                'gasPrice': w3.to_wei(5, 'gwei'),
                'nonce': nonce,
        })

    # Sign and send transaction
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f'Swap ransaction {tx_hash.hex()}.')


def send_token(token, to_address, amount):
    to_address = w3.to_checksum_address(to_address)
    from_address = w3.to_checksum_address(public_key)
    tx_hash = ''
    if token == 'ETH':
        nonce = w3.eth.get_transaction_count(from_address)

        tx = {
            'to': to_address,
            'value': amount,
            "nonce": nonce
        }

        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        print(f'Transaction {tx_hash.hex()} sent {amount} Wei to {to_address}')
    else:
        nonce = w3.eth.get_transaction_count(from_address)
        abi = ABIS[token]
        token = w3.to_checksum_address(TOKEN_ADDRESSES[token])
        token_contract = w3.eth.contract(address=token, abi=abi)

        tx = token_contract.functions.transfer(to_address, amount).build_transaction({
            'gas': 70000,
            'gasPrice': w3.to_wei(5, 'gwei'),
            'nonce': nonce,
        })

        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        print(f'Transaction {tx_hash.hex()} sent {amount} Wei to {to_address}')

    return tx_hash.hex()


def check_balance(address):
    balances = {}

    for token_name, token_address in TOKEN_ADDRESSES.items():
        if token_name == 'ETH':
            # Get ETH balance
            balance = w3.eth.get_balance(w3.to_checksum_address(address))
            balances[token_name] = w3.from_wei(balance, 'ether')
        else:
            # Get ERC20 token balance
            abi = ABIS[token_name]
            token = w3.to_checksum_address(TOKEN_ADDRESSES[token_name])
            token_contract = w3.eth.contract(address=token, abi=abi)
            token_balance = token_contract.functions.balanceOf(w3.to_checksum_address(address)).call()
            balance = w3.from_wei(token_balance, 'ether')
            balances[token_name] = balance

    # Get USD equivalent
    usd_rates = get_usd_rates()
    for token_name, balance in balances.items():
        balances[token_name] = {
            'balance': balance,
            'usd_value': balance * usd_rates[token_name]
        }

    return balances


def get_usd_rates():
    rates = {}


    for token in TOKEN_ADDRESSES.keys():
        if token == 'WETH':
            COIN_SYMBOL = f'ETHUSDT'
        else:
            COIN_SYMBOL = f'{token}USDT'  # Replace with the symbol of the coin you want to check
        url = f'https://api.binance.com/api/v3/ticker/price?symbol={COIN_SYMBOL}'
        response = requests.get(url)
        data = response.json()
        price = data['price']
        print(f'The current price of {COIN_SYMBOL} is {price}')
        rates[token] = float(price)

    return rates

# Example usage:

# Generate new account
account = generate_account()
print(account)

# # Swap 1 ETH for WETH
# swap_token('ETH', 'WETH', 1)
#
# # Send 1 UNI to another address
# send_token('UNI', '<RECIPIENT ADDRESS HERE>', 1)

# Check wallet balance
print(get_usd_rates())
balance = check_balance(public_key)
print(balance)
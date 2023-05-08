from web3 import Web3
from eth_account import Account
import requests
import os
from dotenv import load_dotenv
from web3.middleware import geth_poa_middleware

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

public_key = os.environ.get("PUBLIC_KEY")
private_key = os.environ.get("PRIVATE_KEY")
provider = os.environ.get("PROVIDER")

w3 = Web3(Web3.HTTPProvider(provider))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)
Account.enable_unaudited_hdwallet_features()


# Define token addresses
TOKEN_ADDRESSES = {
    'MATIC': '0x0000000000000000000000000000000000000000',
    'WETH': '0x195fe6EE6639665CCeB15BCCeB9980FC445DFa0B',
    'WMATIC': '0x9c3C9283D3e44854697Cd22D3Faa240Cfb032889'
}

ABIS = {
    'WETH': '',
    'WMATIC': '',
    'UNISWAP_ROUTER': '',
    'UNISWAP_FACTORY': ''
}

with open('abi/wmatic.abi', 'r') as abi:
    ABIS['WMATIC'] = abi.readline()

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
    amount = w3.to_wei(amount, "ether")
    factory_abi = ABIS["UNISWAP_FACTORY"]
    router_abi = ABIS["UNISWAP_ROUTER"]
    erc20_abi = ABIS["WETH"]
    wmatic_abi = ABIS["WMATIC"]

    factory_address = w3.to_checksum_address('0x1F98431c8aD98523631AE4a59f267346ea31F984')
    router_address = w3.to_checksum_address('0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45')

    # Create contract objects for the Uniswap factory and router contracts
    factory_contract = w3.eth.contract(address=factory_address, abi=factory_abi)
    router_contract = w3.eth.contract(address=router_address, abi=router_abi)
    wmatic_contract = w3.eth.contract(address=w3.to_checksum_address(TOKEN_ADDRESSES['WMATIC']), abi=wmatic_abi)
    deadline = w3.eth.get_block('latest')['timestamp'] + 60

    nonce = w3.eth.get_transaction_count(w3.to_checksum_address(public_key))
    tx = ''
    if from_token == 'MATIC':
        if to_token == 'WMATIC':

            tx = wmatic_contract.functions.deposit().build_transaction({
                'gas': 300000,
                'gasPrice': w3.to_wei(5, 'gwei'),
                'nonce': nonce,
                'value': amount,
                'chainId': 80001
            })
    else:
        tx = router_contract.functions.swapExactTokensForTokens(
            amount,
            0,
            [w3.to_checksum_address(TOKEN_ADDRESSES[from_token]), w3.to_checksum_address(TOKEN_ADDRESSES[to_token])],
            public_key,
            deadline
        ).build_transaction({
            'gas': 300000,
            'gasPrice': w3.to_wei(5, 'gwei'),
            'nonce': nonce,
            'chainId': 80001
        })

    # Sign and send transaction
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print(tx_hash.hex())
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f'Swap ransaction {tx_hash.hex()}.')


def send_token(token, to_address, amount):
    amount = w3.to_wei(amount, "ether")
    to_address = w3.to_checksum_address(to_address)
    from_address = w3.to_checksum_address(public_key)
    tx_hash = ''
    if token == 'MATIC':
        nonce = w3.eth.get_transaction_count(from_address)

        tx = {
            "from": from_address,
            'to': to_address,
            'value': amount,
            "nonce": nonce,
            'gas': 70000,
            'gasPrice': w3.to_wei(5, 'gwei'),
            'chainId': 80001
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
            'chainId': 80001
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
        if token_name == 'MATIC':
            # Get ETH balance
            balance = w3.eth.get_balance(w3.to_checksum_address(address))
            balances[token_name] = float(w3.from_wei(balance, 'ether'))
        else:
            # Get ERC20 token balance
            abi = ABIS[token_name]
            token = w3.to_checksum_address(TOKEN_ADDRESSES[token_name])
            token_contract = w3.eth.contract(address=token, abi=abi)
            token_balance = token_contract.functions.balanceOf(w3.to_checksum_address(address)).call()
            balance = float(w3.from_wei(token_balance, 'ether'))
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
        elif token == "WMATIC":
            COIN_SYMBOL = 'MATICUSDT'
        else:
            COIN_SYMBOL = f'{token}USDT'  # Replace with the symbol of the coin you want to check
        url = f'https://api.binance.com/api/v3/ticker/price?symbol={COIN_SYMBOL}'
        response = requests.get(url)
        data = response.json()
        price = data['price']
        print(f'The current price of {COIN_SYMBOL} is {price}')
        rates[token] = float(price)

    return rates

# only Goerly testnet!!!
def send_to_base(amount):
    amount = w3.to_wei(amount, "wei")
    to_address = w3.to_checksum_address("0xe93c8cD0D409341205A592f8c4Ac1A5fe5585cfA")
    from_address = w3.to_checksum_address(public_key)
    tx_hash = ''
    nonce = w3.eth.get_transaction_count(from_address)

    tx = {
        "from": from_address,
        'to': to_address,
        'value': amount,
        "nonce": nonce,
        'gas': 300000,
        'gasPrice': w3.to_wei(20, 'gwei'),
        'chainId': 5
    }

    # Sign and send transaction
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f'Transaction {tx_hash.hex()} sent {amount} Wei to {to_address}')

    return tx_hash.hex()
# Example usage:

# Generate new account
account = generate_account()
print(account)


swap_token('MATIC', 'WMATIC', 0.0001)

#send_token('MATIC', '0x58b66a4305325772F070e023C0CEf6652bE15c40', 0.0001)

balance = check_balance(public_key)
print(balance)
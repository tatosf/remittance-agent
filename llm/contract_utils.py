# Copyright (c) 2024 Blockchain at Berkeley.  All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# SPDX-License-Identifier: MIT

import json
import os
import secrets
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Sepolia testnet contract addresses
SEPOLIA_CONTRACTS = {
    "USDC": "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",
    "EURC": "0x08210F9170F89Ab7658F0B5E3fF39b0E03C594D4",
    "tUSD": "0xF038E27507405954a1B59D37b936f0226C6034AC",
    "tEUR": "0x6F2f88340B027Cc6b8a551912A30e957aC59cb8b",
    "TestRemittanceBridge": "0x522BdF8af3415aa281e25481A1D402869E161e36",
}

# Token decimals
TOKEN_DECIMALS = {"USDC": 6, "EURC": 6, "tUSD": 6, "tEUR": 6}

# Simulated gas price (in gwei)
GAS_PRICE = 50 * 10**9  # 50 gwei

# Sepolia chain ID
CHAIN_ID = 11155111


# Simplified function to generate a transaction hash
def generate_tx_hash():
    return f"0x{secrets.token_hex(32)}"


# Load contract ABIs
def load_contract_abis():
    """
    Load contract ABIs from the contract_abis.json file
    """
    contract_abis_path = (
        Path(__file__).parent.parent / "contracts" / "contract_abis.json"
    )
    with open(contract_abis_path, "r") as f:
        return json.load(f)


CONTRACT_ABIS = load_contract_abis()


# Utility function to format an address (without actually checksumming it)
def format_address(address):
    if not address.startswith("0x"):
        address = "0x" + address
    return address.lower()


# Helper functions for contract interaction
def format_transaction_for_signing(tx_data, user_address):
    """
    Format a transaction for signing by the frontend
    """
    # Make sure user address is properly formatted
    user_address = format_address(user_address)

    # Create a transaction object that the frontend can handle
    formatted_tx = {
        "to": tx_data.get("to"),
        "from": user_address,
        "data": tx_data.get("data"),
        "value": tx_data.get("value", 0),
        "gasLimit": tx_data.get(
            "gas", 200000
        ),  # Changed from "gas" to "gasLimit" for ethers.js compatibility
        "gasPrice": tx_data.get("gasPrice", GAS_PRICE),
        # Use a simpler nonce approach - let the wallet/provider determine the nonce
        # This avoids potential nonce issues with consecutive transactions
        "chainId": CHAIN_ID,
    }

    # Don't set a nonce - let the wallet provider (ethers.js) handle nonce management
    # This helps avoid nonce issues

    return formatted_tx


def generate_tusd_faucet_tx(user_address, amount):
    """
    Generate a transaction for getting tUSD tokens from the faucet function
    This mints test tokens directly to the user's wallet
    """
    # Convert user input amount to proper tUSD decimal representation (6 decimals)
    tusd_amount = int(float(amount) * 10 ** TOKEN_DECIMALS["tUSD"])

    # Create function signature + encoded parameters for mint(uint256)
    # Function selector for mint function
    function_selector = "a0712d68"  # keccak256("mint(uint256)") first 4 bytes

    # Encode the parameters (simplified)
    amount_encoded = f"{tusd_amount:064x}"

    # Concatenate everything with a single 0x prefix
    data = f"0x{function_selector}{amount_encoded}"

    # Build a simulated transaction with a higher gas limit to ensure it completes
    tx = {
        "to": SEPOLIA_CONTRACTS["tUSD"],
        "from": format_address(user_address),
        "data": data,
        "gas": 200000,  # Increased from 100000 to 200000
        "gasPrice": 55 * 10**9,  # Slightly higher gas price (55 gwei)
        "chain": "sepolia",
        "value": 0,  # Explicitly set value to 0
    }

    return format_transaction_for_signing(tx, user_address)


def generate_tusd_approval_tx(user_address, spender_address, amount):
    """
    Generate a transaction for approving tUSD spending on Sepolia
    """
    # Convert user input amount to proper tUSD decimal representation (6 decimals)
    tusd_amount = int(float(amount) * 10 ** TOKEN_DECIMALS["tUSD"])

    # Create simulated approval transaction data
    data = (
        f"0x095ea7b3{format_address(spender_address)[2:].zfill(64)}{tusd_amount:064x}"
    )

    # Build a simulated transaction
    tx = {
        "to": SEPOLIA_CONTRACTS["tUSD"],
        "from": format_address(user_address),
        "data": data,
        "gas": 100000,
        "gasPrice": GAS_PRICE,
        "chain": "sepolia",
    }

    return format_transaction_for_signing(tx, user_address)


def generate_teur_approval_tx(user_address, spender_address, amount):
    """
    Generate a transaction for approving tEUR spending on Sepolia
    """
    # Convert user input amount to proper tEUR decimal representation (6 decimals)
    teur_amount = int(float(amount) * 10 ** TOKEN_DECIMALS["tEUR"])

    # Create simulated approval transaction data
    data = (
        f"0x095ea7b3{format_address(spender_address)[2:].zfill(64)}{teur_amount:064x}"
    )

    # Build a simulated transaction
    tx = {
        "to": SEPOLIA_CONTRACTS["tEUR"],
        "from": format_address(user_address),
        "data": data,
        "gas": 100000,
        "gasPrice": GAS_PRICE,
        "chain": "sepolia",
    }

    return format_transaction_for_signing(tx, user_address)


def generate_test_remittance_tx(user_address, amount, recipient):
    """
    Generate a transaction for the test remittance bridge (tUSD to tEUR) on Sepolia
    """
    # Convert user input amount to proper tUSD decimal representation (6 decimals)
    tusd_amount = int(float(amount) * 10 ** TOKEN_DECIMALS["tUSD"])

    # Correct function selector from Remix transaction
    function_selector = "ff6dc6cf"  # The actual function selector used in Remix

    # Format amount as 32 bytes hex
    amount_encoded = f"{tusd_amount:064x}"

    # Use the exact working calldata format from Remix, replacing only the amount
    # Structure: function_selector + amount + string offset + string length + string data
    data = f"0x{function_selector}{amount_encoded}0000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000001d53616e746961676f20746573742031737420747261736e616374696f6e000000"

    # Build a simulated transaction
    tx = {
        "to": SEPOLIA_CONTRACTS["TestRemittanceBridge"],
        "from": format_address(user_address),
        "data": data,
        "gas": 300000,
        "gasPrice": GAS_PRICE,
        "chain": "sepolia",
    }

    return format_transaction_for_signing(tx, user_address)


def simulate_test_remittance_cost(user_address, usd_amount):
    """
    Simulate the cost of a remittance transaction using real-world exchange rates
    """
    # Use fixed exchange rates for simulation (these would be fetched from APIs in production)
    usd_to_usdc_rate = 1.005  # $1 USD = 1.005 USDC (0.5% fee)
    usdc_to_eurc_rate = 0.92  # 1 USDC = 0.92 EURC (EUR/USD exchange rate)
    eurc_to_eur_rate = 1.01  # 1 EURC = 1.01 EUR (1% fee)

    # Estimate network fees (gas costs) - this would be calculated based on gas price and gas used
    estimated_gas = 300000  # Gas used for the whole remittance flow
    gas_price_gwei = GAS_PRICE / 10**9  # Convert gas price to gwei
    eth_price_usd = (
        3000  # Assume ETH price is $3000 (this would be fetched from an API)
    )

    # Calculate network fee in USD
    network_fee_usd = (estimated_gas * gas_price_gwei * eth_price_usd) / 10**9

    # Calculate service fee (0.5% of the amount)
    service_fee_usd = float(usd_amount) * 0.005

    # Calculate total cost
    total_cost_usd = network_fee_usd + service_fee_usd

    # Generate a transaction hash for traceability
    tx_hash = generate_tx_hash()

    return {
        "usd_amount": float(usd_amount),
        "usdc_amount": float(usd_amount) / usd_to_usdc_rate,
        "eurc_amount": (float(usd_amount) / usd_to_usdc_rate) * usdc_to_eurc_rate,
        "eur_amount": (float(usd_amount) / usd_to_usdc_rate)
        * usdc_to_eurc_rate
        / eurc_to_eur_rate,
        "exchange_rates": {
            "usd_to_usdc": usd_to_usdc_rate,
            "usdc_to_eurc": usdc_to_eurc_rate,
            "eurc_to_eur": eurc_to_eur_rate,
        },
        "fees": {
            "network_fee_usd": network_fee_usd,
            "service_fee_usd": service_fee_usd,
            "total_cost_usd": total_cost_usd,
        },
        "transaction_hash": tx_hash,
        "requires_signature": False,
        "chain": "sepolia",
    }

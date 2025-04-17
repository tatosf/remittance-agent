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
from .utils import create_open_ai_client, load_schema
from .contract_utils import (
    generate_tusd_approval_tx,
    generate_test_remittance_tx,
    generate_teur_approval_tx,
    simulate_test_remittance_cost,
    generate_tusd_faucet_tx,
    SEPOLIA_CONTRACTS,
)

# Load the JSON schema for remittance
remittance_schema = load_schema("schemas/remittance.json")

# Initialize OpenAI client
client = create_open_ai_client()

# Contract addresses from SEPOLIA_CONTRACTS
TEST_REMITTANCE_BRIDGE_ADDRESS = SEPOLIA_CONTRACTS["TestRemittanceBridge"]


def process_remittance_intent(user_input, use_test_tokens=True):
    """
    Process a remittance intent from natural language to structured data for Sepolia testnet
    Input: User's natural language request
    Output: Structured JSON for the remittance flow using test tokens

    Parameters:
    - user_input: Natural language input from the user
    - use_test_tokens: Boolean parameter kept for backward compatibility, but always True
    """
    # System message explaining the task
    system_message = {
        "role": "system",
        "content": (
            "You are a helpful assistant that converts natural language for cross-border "
            "remittance (USD to EUR) into a JSON format according to the provided schema. "
            "The flow involves converting USD to USDC, then USDC to EURC, and finally EURC to EUR. "
            "This will be executed on the Sepolia testnet. "
            "Focus on extracting the source (USD), target (EUR), amount, and recipient information."
        ),
    }

    schema_message = {
        "role": "system",
        "content": "Remittance Schema:\n" + json.dumps(remittance_schema, indent=2),
    }

    examples_message = {
        "role": "system",
        "content": (
            "Examples:\n"
            "1. User: 'Send $100 to my friend John in Europe'\n"
            '   Output: {"source_currency": "USD", "target_currency": "EUR", "amount": 100, '
            '"recipient_name": "John", "recipient_address": "default"}\n\n'
            "2. User: 'I want to remit 50 dollars to 0x1234abcd... in euros'\n"
            '   Output: {"source_currency": "USD", "target_currency": "EUR", "amount": 50, '
            '"recipient_address": "0x1234abcd..."}\n\n'
            "Always default to USD as source and EUR as target for cross-border remittance. "
            "All transactions will be executed on the Sepolia testnet."
        ),
    }

    # User message with the input text
    user_message = {"role": "user", "content": user_input}

    # Sending the prompt to the language model
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[system_message, schema_message, examples_message, user_message],
        temperature=0.1,  # Lower temperature for more deterministic outputs
    )

    # Extract the response and parse it as JSON
    response_text = completion.choices[0].message.content.strip()

    # Extract JSON from the response if it's wrapped in text
    if "```json" in response_text:
        # Extract JSON from markdown code block
        json_start = response_text.find("```json") + 7
        json_end = response_text.find("```", json_start)
        json_str = response_text[json_start:json_end].strip()
    elif "```" in response_text:
        # Extract JSON from generic code block
        json_start = response_text.find("```") + 3
        json_end = response_text.find("```", json_start)
        json_str = response_text[json_start:json_end].strip()
    else:
        # Assume the entire response is JSON
        json_str = response_text

    try:
        parsed_data = json.loads(json_str)
    except json.JSONDecodeError:
        # If we still can't parse, try to extract anything that looks like JSON
        try:
            # Find content between curly braces
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed_data = json.loads(json_str)
            else:
                raise Exception("Could not extract JSON content")
        except:
            raise Exception(
                f"Failed to parse the model response as JSON: {response_text}"
            )

    # Validate and set defaults
    parsed_data["source_currency"] = parsed_data.get("source_currency", "USD")
    parsed_data["target_currency"] = parsed_data.get("target_currency", "EUR")
    amount = parsed_data.get("amount", 0)
    recipient_address = parsed_data.get("recipient_address", "")
    recipient_name = parsed_data.get("recipient_name", "")

    # If recipient_address is not provided or is "default", use a placeholder
    if not recipient_address or recipient_address == "default":
        recipient_address = "0x0000000000000000000000000000000000000000"

    # Get the cost simulation data
    cost_simulation = simulate_test_remittance_cost(recipient_address, amount)

    # Create the remittance flow with test tokens
    result = {
        **parsed_data,
        "chain": "sepolia",  # Explicitly set to Sepolia
        "using_test_tokens": True,  # Flag to indicate we're using test tokens
        "transaction_flow": {
            "step1": {
                "name": "Get tUSDC Tokens",
                "description": f"Get test USD tokens directly to your wallet",
                "tx_data": generate_tusd_faucet_tx(recipient_address, amount),
                "requires_signature": True,
                "status": "waiting_for_signature",
                "explain": "This step will mint test USD tokens directly to your wallet. These tokens represent USD for testing purposes.",
            },
            "step2": {
                "name": "tUSDC Approval",
                "description": f"Approve the TestRemittanceBridge contract to spend your tUSDC",
                "tx_data": generate_tusd_approval_tx(
                    recipient_address, TEST_REMITTANCE_BRIDGE_ADDRESS, amount
                ),
                "requires_signature": True,
                "status": "waiting_for_signature",
                "explain": "This step approves the TestRemittanceBridge contract to spend your tUSDC tokens on your behalf.",
            },
            "step3": {
                "name": "USD to EUR Conversion",
                "description": f"Convert {amount} tUSDC to tEURC via TestRemittanceBridge",
                "tx_data": generate_test_remittance_tx(
                    recipient_address,
                    amount,
                    recipient_name or "Remittance Recipient",
                ),
                "requires_signature": True,
                "status": "waiting_for_signature",
                "explain": "This transaction converts your tUSDC to tEURC at the current exchange rate, simulating an international remittance.",
            },
            "step4": {
                "name": "Check tEURC Balance",
                "description": f"Check your tEURC balance after remittance",
                "check_balance": {
                    "token_address": SEPOLIA_CONTRACTS["tEUR"],
                },
                "requires_signature": False,
                "status": "waiting_for_execution",
                "explain": "This step checks your tEURC balance after the remittance is complete.",
            },
        },
        "status_summary": {
            "total_steps": 4,
            "current_step": 1,
            "completed_steps": 0,
            "usd_amount": amount,
            "estimated_eur_amount": amount * 0.9,  # Simulated exchange rate and fees
            "recipient": recipient_name or recipient_address,
            "network": "Sepolia Testnet",
            "using_test_tokens": True,
        },
        "cost_simulation": cost_simulation,
        "token_addresses": {
            "tUSD": SEPOLIA_CONTRACTS["tUSD"],
            "tEUR": SEPOLIA_CONTRACTS["tEUR"],
            "bridge": SEPOLIA_CONTRACTS["TestRemittanceBridge"],
        },
    }

    return result

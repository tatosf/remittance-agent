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

# Load the JSON schemas for swap and simple transfer
swap_schema = load_schema("schemas/swap.json")
transfer_schema = load_schema("schemas/transfer.json")
remittance_schema = load_schema("schemas/remittance.json")

# Initialize OpenAI client
client = create_open_ai_client()


def classify_transaction(transaction_text):
    # System message explaining the task
    system_message = {
        "role": "system",
        "content": "Determine if the following transaction text is for a token swap, a transfer, or a cross-border remittance (USD to EUR). Use the appropriate schema to understand the transaction. Return '1' for transfer, '2' for swap, '3' for buying crypto with fiat, '4' for remittance, and '0' for none of these. Do not output anything besides this number. If one number is classified for the output, make sure to omit the other numbers in your generated response.",
    }

    # Messages to set up schema contexts
    swap_schema_message = {
        "role": "system",
        "content": "[Swap Schema] Token Swap Schema:\n"
        + json.dumps(swap_schema, indent=2),
    }
    transfer_schema_message = {
        "role": "system",
        "content": "[Transfer Schema] Simple Transfer/Send Schema:\n"
        + json.dumps(transfer_schema, indent=2),
    }
    remittance_schema_message = {
        "role": "system",
        "content": "[Remittance Schema] Cross-Border Remittance (USD to EUR) Schema:\n"
        + json.dumps(remittance_schema, indent=2),
    }

    # Examples to help distinguish between transfer and remittance
    examples_message = {
        "role": "system",
        "content": """
        Examples to distinguish between transfer and remittance:
        
        Transfer examples (return '1'):
        - "Send 10 USDC to 0x123abc..."
        - "Transfer 5 ETH to vitalik.eth"
        - "Move 20 WETH from my wallet to 0xdef456..."
        
        Remittance examples (return '4'):
        - "Send $100 to my family in Europe"
        - "Remit 50 USD to EUR for my friend"
        - "I want to convert 200 dollars to euros and send it to 0x789xyz..."
        - "Cross-border payment of $75 to my friend in the EU"
        
        The key difference is that remittance involves cross-border currency conversion (USD to EUR),
        while transfer is moving tokens directly from one address to another without currency conversion.
        """,
    }

    # User message with the transaction text
    user_message = {"role": "user", "content": transaction_text}

    # Sending the prompt to ChatGPT
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            system_message,
            swap_schema_message,
            transfer_schema_message,
            remittance_schema_message,
            examples_message,
            user_message,
        ],
    )

    # Extracting and interpreting the last message from the completion
    response = completion.choices[0].message.content.strip()
    print("classification: ", response)
    return get_valid_response(response)


def get_valid_response(response):
    valid_responses = ["0", "1", "2", "3", "4"]
    found = None

    for valid in valid_responses:
        # Count the occurrences of each valid response in the string
        if response.count(valid) == 1:
            if found is not None:
                # If another valid response was already found, return 0
                return 0
            found = int(valid)  # Store the found valid response

    return found if found is not None else 0


# Add a new function for handling test token remittance
def process_transaction(transaction_text, use_test_tokens=False):
    """
    Process a transaction text and route it to the appropriate handler.

    Parameters:
    - transaction_text: Text describing the transaction
    - use_test_tokens: Boolean indicating whether to use test tokens for remittance

    Returns:
    - Structured transaction data
    """
    from .remittance import process_remittance_intent
    from .transfer import process_transfer_intent
    from .swap import process_swap_intent

    # Classify the transaction
    transaction_type = classify_transaction(transaction_text)

    # Process based on the transaction type
    if transaction_type == 1:  # Transfer
        return {
            "transaction_type": "transfer",
            "response": process_transfer_intent(transaction_text),
        }
    elif transaction_type == 2:  # Swap
        return {
            "transaction_type": "swap",
            "response": process_swap_intent(transaction_text),
        }
    elif transaction_type == 3:  # Buy
        return {
            "transaction_type": "buy",
            "response": {"error": "Buy functionality has been removed"},
        }
    elif transaction_type == 4:  # Remittance
        return {
            "transaction_type": "remittance",
            "response": process_remittance_intent(transaction_text, use_test_tokens),
        }
    else:  # Unknown
        return {
            "transaction_type": "unknown",
            "response": {"error": "Could not determine the transaction type."},
        }

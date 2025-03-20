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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
import json
from llm import swap, handler, transfer, buy

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allows only localhost origin
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

order = """
Prompt
"""


class UserQuery(BaseModel):
    question: str


@app.post("/answer/")
async def get_answer(query: UserQuery):
    print("DEBUG: Entered get_answer with query:", query.question)
    try:
        classification = handler.classify_transaction(query.question)
        print("DEBUG: Classification result:", classification)
    except Exception as e:
        print("DEBUG: Exception during classification:", e)
        raise HTTPException(status_code=500, detail=str(e))

    try:
        if classification == 0:
            print("DEBUG: Classification is 0, unable to classify intent.")
            raise HTTPException(
                status_code=500, detail="Our backend was unable to classify your intent"
            )
        elif classification == 1:
            print("DEBUG: Detected transfer intent.")
            response = transfer.convert_transfer_intent(query.question)
            query_type = "transfer"
        elif classification == 2:
            print("DEBUG: Detected swap intent.")
            response = swap.convert_transaction(query.question)
            query_type = "swap"
        elif classification == 3:
            print("DEBUG: Detected buy intent.")
            response = buy.convert_buy_intent(query.question)
            query_type = "buy"
        else:
            print("DEBUG: Unexpected classification value:", classification)
            raise HTTPException(
                status_code=500, detail="Unexpected classification result"
            )

        print("DEBUG: Conversion response:", response)
    except Exception as e:
        print("DEBUG: Exception during conversion:", e)
        raise HTTPException(status_code=500, detail=str(e))

    return {"transaction_type": query_type, "response": response}


@app.post("/swap/")
async def get_swap(query: UserQuery):
    try:
        response = swap.convert_transaction(query.question)
        return {"transaction_type": "swap", response: response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transfer/")
async def get_transfer(query: UserQuery):
    try:
        response = transfer.convert_transfer_intent(query.question)
        return {"transaction_type": "transfer", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/buy/")
async def get_buy(query: UserQuery):
    try:
        response = buy.convert_buy_intent(query.question)
        return {"transaction_type": "buy", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/classify/")
async def classify_query(query: UserQuery):
    try:
        response = handler.classify_transaction(query.question)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
import paypalrestsdk
import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# PayPal configuration
paypalrestsdk.configure({
    "mode": "sandbox",  # or "live" for production
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_CLIENT_SECRET")
})

# Get base URL from environment variable, default to localhost for development
BASE_URL = os.getenv("BASE_URL")


@app.post("/create-order")
async def create_order(request: Request):
    try:
        body = await request.json()
        total_price = body.get('total_price')
        currency = body.get('currency', 'USD')
        
        # Ensure total_price is provided and valid
        if total_price is None:
            raise HTTPException(status_code=400, detail="Total price is required.")
        try:
            total_price = float(total_price)
        except ValueError:
            raise HTTPException(status_code=400, detail="Total price must be a valid number.")
        
        # Ensure total_price is not zero or negative
        if total_price <= 0:
            raise HTTPException(status_code=400, detail="Invalid total amount.")

        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "transactions": [{
                "amount": {
                    "total": f"{total_price:.2f}",  # Use provided total price
                    "currency": currency  # Use provided currency
                },
                "description": "This is the payment transaction description."
            }],
            "redirect_urls": {
                "return_url": f"{BASE_URL}/execute-payment",
                "cancel_url": f"{BASE_URL}/"
            },
            "application_context": {
                "brand_name": "ASAS For Furniture",
                # "shipping_preference": "NO_SHIPPING",
                # "user_action":"PAY_NOW"
            }
        })
        
        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = str(link.href)
                    logger.info({"approval_url": approval_url})
                    return {"approval_url": approval_url, "paymentID": payment.id}
        
        logger.error(f"PayPal Payment Creation Error: {payment.error}")
        raise HTTPException(status_code=400, detail=payment.error)

    except Exception as e:
        logger.error(f"An error occurred while creating order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/execute-payment/")
async def execute_payment(paymentId: str = Query(...), PayerID: str = Query(...)):
    try:
        payment = paypalrestsdk.Payment.find(paymentId)
        logger.info({"payerId": PayerID})

        if payment.execute({"payer_id": PayerID}):
            logger.info("Payment executed successfully")
            return {"status": "Payment executed successfully"}
        
        error_details = payment.error
        logger.error(f"PayPal Payment Execution Error: {error_details}")
        raise HTTPException(status_code=400, detail=error_details)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/paypal/webhook")
async def handle_webhook(request: Request):
    try:
        body = await request.json()
        event_type = body.get("event_type")

        if event_type == "PAYMENT.SALE.COMPLETED":
            # Handle payment sale completed event
            logger.info("Payment sale completed event received")
            # Implement your logic here
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"An error occurred while handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


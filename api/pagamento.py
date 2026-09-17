import time
import uuid
import random

class PaymentError(Exception):
    pass

def process_payment(amount: float, method: str = "credit_card") -> dict:
    if amount <= 0:
        raise PaymentError("Valor inválido para pagamento.")

    transaction_id = str(uuid.uuid4())
    time.sleep(1.5)
    success = random.random() > 0.1

    if not success:
        raise PaymentError("Pagamento recusado. Tente novamente.")

    return {
        "status": "aprovado",
        "transaction_id": transaction_id,
        "amount": amount,
        "method": method,
    }
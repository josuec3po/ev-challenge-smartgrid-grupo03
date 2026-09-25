import time
import uuid

class PaymentError(Exception):
    pass

def process_payment(amount: float, method: str) -> dict:
    if amount <= 0:
        raise PaymentError("Valor inválido para pagamento.")

    transaction_id = str(uuid.uuid4())
    time.sleep(1.5)
    # Recusa aleatória removida para a demo: aqui sempre aprova (exceto valor inválido acima).
    # Se quiser reativar depois, é só trazer de volta o "random.random() > 0.1".

    return {
        "status": "aprovado",
        "transaction_id": transaction_id,
        "amount": amount,
        "method": method,
    }
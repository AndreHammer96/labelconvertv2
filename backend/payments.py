# backend/payments.py
"""
Aqui futuramente você adicionará integração com Gerencianet / Asaas.

Funções esperadas:
- create_pix_charge(plano, user): retorna txid, qrcode, imagem
- handle_webhook(payload, db): atualiza assinatura e user.plano

Por enquanto, o fluxo de /assinatura/{plano_id} usa um mock (simulação de PIX).
"""

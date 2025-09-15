# Mock blockchain MATIC payments for development

def process_payment(amount, recipient_address, sender_address=None):
    """Mock payment processing"""
    return {
        'success': True,
        'transaction_id': f'mock_tx_{hash(str(amount) + recipient_address)}',
        'amount': amount,
        'recipient': recipient_address
    }

def send_to_escrow(amount, escrow_address, sender_address=None):
    """Mock escrow sending"""
    return {
        'success': True,
        'escrow_tx_id': f'escrow_tx_{hash(str(amount) + escrow_address)}',
        'amount': amount,
        'escrow_address': escrow_address
    }

def send_to_admin(amount, admin_address, sender_address=None):
    """Mock admin payment"""
    return {
        'success': True,
        'admin_tx_id': f'admin_tx_{hash(str(amount) + admin_address)}',
        'amount': amount,
        'admin_address': admin_address
    }

def release_from_escrow(escrow_tx_id, recipient_address):
    """Mock escrow release"""
    return {
        'success': True,
        'release_tx_id': f'release_tx_{hash(escrow_tx_id + recipient_address)}',
        'escrow_tx_id': escrow_tx_id,
        'recipient': recipient_address
    }
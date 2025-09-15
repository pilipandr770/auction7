# Mock blockchain payments module for development
def get_user_discount(wallet_address):
    """
    Mock function to get user discount based on wallet address
    In production, this would connect to blockchain to check token holdings
    """
    # Return a mock 5% discount for demo purposes
    if wallet_address:
        return 5.0
    return 0.0
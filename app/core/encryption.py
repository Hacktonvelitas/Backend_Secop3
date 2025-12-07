from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from app.core.config import settings

BLOCK_SIZE = 16

def _get_key() -> bytes:
    """
    Obtiene la clave de encriptación desde la configuración.
    Asegura que sea bytes y tenga una longitud válida (16, 24 o 32 bytes).
    """
    key = settings.encryption_key
    if isinstance(key, str):
        key = key.encode('utf-8')
    if len(key) not in (16, 24, 32):
        raise ValueError(f"La clave de encriptación debe tener 16, 24 o 32 bytes. Longitud actual: {len(key)}")
    
    return key

def encrypt_data(data: bytes) -> bytes:
    key = _get_key()
    iv = get_random_bytes(BLOCK_SIZE)
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    padded_data = pad(data, BLOCK_SIZE)
    
    encrypted_data = cipher.encrypt(padded_data)

    return iv + encrypted_data

def decrypt_data(data: bytes) -> bytes:
    key = _get_key()
    
    iv = data[:BLOCK_SIZE]
    encrypted_content = data[BLOCK_SIZE:]
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    decrypted_padded = cipher.decrypt(encrypted_content)
    
    # Remover padding
    return unpad(decrypted_padded, BLOCK_SIZE)

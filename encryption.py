from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
import base64
import os

class KeyExchange:
    def __init__(self):
        # Generate RSA key pair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def get_public_key_bytes(self):
        # Get public key in bytes format for sending over network.
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def encrypt_symmetric_key(self, public_key_bytes, symmetric_key):
        # Encrypt symmetric key using received public key.
        public_key = serialization.load_pem_public_key(public_key_bytes)
        return public_key.encrypt(
            symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def decrypt_symmetric_key(self, encrypted_symmetric_key):
        # Decrypt symmetric key using private key.
        return self.private_key.decrypt(
            encrypted_symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

class MessageEncryption:
    def __init__(self, symmetric_key=None):
        if symmetric_key is None:
            symmetric_key = Fernet.generate_key()
        self.fernet = Fernet(symmetric_key)
        self.symmetric_key = symmetric_key

    def get_symmetric_key(self):
        # Get the symmetric key.
        return self.symmetric_key

    def encrypt_message(self, message):
        # Encrypt a string message.
        return self.fernet.encrypt(message.encode())

    def decrypt_message(self, encrypted_message):
        # Decrypt an encrypted message.
        return self.fernet.decrypt(encrypted_message).decode()

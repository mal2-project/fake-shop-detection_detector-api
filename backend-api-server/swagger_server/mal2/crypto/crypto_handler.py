import os
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from binascii import hexlify
from OpenSSL import crypto, SSL
import binascii
from datetime import datetime, date, timedelta
import fnmatch
import os

rsakeys_loc = os.path.abspath(os.getcwd())+"/swagger_server/resources/secret/rsakeys/".replace('/',os.path.sep)
sslkeys_loc = os.path.abspath(os.getcwd())+"/swagger_server/resources/secret/ssl/".replace('/',os.path.sep)

def initKeys():
    """Creates new crypto keys if not exist
    """
    #check app key exists or create (used for password and token encryption - always keep)
    if(not os.path.exists(rsakeys_loc+'private_app_key.pem')):
        os.makedirs(rsakeys_loc, exist_ok=True)
        createRSAKeyPair(rsakeys_loc, "app")
    #check ssl cert exists or create
    if(not os.path.exists(sslkeys_loc+'privkey.pem')):
        os.makedirs(sslkeys_loc, exist_ok=True)
        createSelfSignedX509Cert(sslkeys_loc)

def encrypt(message:str, asAscii=True, key_name="app"):
    """[encrypts a given message using the apps key]
    Args:
        message (str): [message to encrypt]
        asAscii (bool): [encrypted message output returned as binary (False) or as ascii (default:True)
        key_file(str): [name of the key file to use (default:app -> translates to public_app_key.pem")]
    """
    #check required keys exist before every encryption
    initKeys()

    key_name= "public_{}_key.pem".format(key_name)

    pu_key = RSA.importKey(open(rsakeys_loc+key_name, 'r').read())
    cipher = PKCS1_OAEP.new(key=pu_key)
    #Encrypting the message with the PKCS1_OAEP object
    bmessage = message.encode('ascii')
    cipher_text = cipher.encrypt(bmessage)
    if(asAscii):
        #convert output from binary (output of PKCS1_OAEP) to ascii
        cipher_text = binascii.hexlify(bytearray(cipher_text)).decode('ascii')
    return cipher_text

def decrypt(cipher_text:str, fromAscii=True, key_name="app"):
    """[decrypts a given message using the apps key]
    Args:
        cipher_text (str): [encrypted message]
        fromAscii (bool): [is cipher_text binary (False) or ascii (default:True)
        key_file(str): [name of the key file to use (default:app -> translates to private_app_key.pem")]
    """
    #check required keys exist before every encryption
    initKeys()

    key_name= "private_{}_key.pem".format(key_name)

    pr_key = RSA.importKey(open(rsakeys_loc+key_name, 'r').read())
    decrypt = PKCS1_OAEP.new(key=pr_key)
    #create immutable object
    acipher_text = cipher_text
    if(fromAscii):
        #convert ascii back to binary, which PKCS1_OAEP is able to handle
        acipher_text = binascii.unhexlify(acipher_text)
    #Decrypting the message with the PKCS1_OAEP object
    decrypted_message = decrypt.decrypt(acipher_text)
    return decrypted_message.decode('ascii')

def createRSAKeyPair(dir_path, keyname, bits=4096):
    """generateds private public RSA keys and stores them on disk

    Args:
        dir_path (str): [output path]
        keyname (str): [Name of the keypair]
    """
    try:
        #Generating private key (RsaKey object) of key length of 1024 bits
        private_key = RSA.generate(bits)
        #Generating the public key (RsaKey object) from the private key
        public_key = private_key.publickey()
        #Converting the RsaKey objects to string 
        private_pem = private_key.exportKey('PEM').decode()
        public_pem = public_key.exportKey('PEM').decode()
        #Export the private and public keys to 'pem' files
        with open(dir_path+'private_'+keyname+'_key.pem', 'w') as pr:
            pr.write(private_pem)
        with open(dir_path+'public_'+keyname+'_key.pem', 'w') as pu:
            pu.write(public_pem)
        print("Creation of RSA keys completed {}".format(keyname))
    except Exception as e:
        print("creation of RSA keys failed: {} {} {}".format(dir_path,keyname,e))

def createSelfSignedX509Cert(dir_path, bits=4096):
    """[creates and stores a self signed x509 ssl certificate]

    Args:
        dir_path ([type]): [description]
        bits (int, optional): [description]. Defaults to 1024.
    """
    try:
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, bits)
        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = "AT"
        cert.get_subject().ST = "Vienna"
        cert.get_subject().L = "Vienna"
        cert.get_subject().O = "AIT - Austrian Institute of Technology GmbH"
        cert.get_subject().OU = "AIT"
        cert.get_subject().CN = "Andrew Lindley"
        cert.get_subject().emailAddress = "andrew.lindley@ait.ac.at"
        cert.set_serial_number(1)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha512')
        with open(dir_path+'cert.pem', "wt") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8"))
        with open(dir_path+'privkey.pem', "wt") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8"))

        print("Creation of X509 SSL certificate completed")
    except Exception as e:
        print("creation of X509 SSL certificate failed: {} {}".format(dir_path,e))
# utils/qr_utils.py
import qrcode
from PIL import Image
import io
from pyzbar.pyzbar import decode
import streamlit as st

def generate_qr_code(data):
    """Generate QR code image from data"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(str(data))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        return img
    except Exception as e:
        st.error(f"QR generation failed: {e}")
        return None

def decode_qr_code(image_file):
    """Decode QR code from uploaded image file"""
    try:
        img = Image.open(image_file)
        decoded_objects = decode(img)
        if decoded_objects:
            return decoded_objects[0].data.decode('utf-8')
        return None
    except Exception as e:
        st.error(f"QR decoding failed: {e}")
        return None
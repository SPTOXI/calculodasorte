# pix_utils.py
"""Utility functions for PIX payload validation and QR code generation.
Provides:
- validar_payload_pix: basic checks that payload follows EMVCo requirements and CRC matches.
- gerar_qrcode_pix_png_base64: generate PNG QR code as a data‑uri base64 string (some banks prefer PNG over SVG).
"""
import base64
import io
import qrcode


def validar_payload_pix(payload: str) -> bool:
    """Validate a PIX copy‑and‑paste payload.
    Checks for required start, presence of CRC tag, and that the CRC matches the calculated value.
    """
    if not payload:
        return False
    # Required prefix for static PIX (format indicator + initiation method)
    if not payload.startswith('000201010211'):
        return False
    # Must contain CRC tag "6304" immediately before the CRC value
    if payload[-8:-4] != "6304":
        return False
    # Extract provided CRC (last 4 characters after "6304")
    crc_provided = payload[-4:]
    # Compute CRC on payload without the CRC value (replace the placeholder with empty string)
    payload_for_crc = payload[:-4]
    # Import calculation function lazily to avoid circular imports
    from database import calcular_crc16_ccitt
    calculated_crc = calcular_crc16_ccitt(payload_for_crc)
    return crc_provided.upper() == calculated_crc.upper()


def gerar_qrcode_pix_png_base64(pix_code: str) -> str:
    """Generate a PNG QR code for a PIX payload and return as data‑uri base64.
    PNG format is widely supported by banking apps and can be more reliable than SVG on some devices.
    """
    if not pix_code:
        return ""
    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(pix_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        stream = io.BytesIO()
        img.save(stream, format="PNG")
        png_bytes = stream.getvalue()
        png_base64 = base64.b64encode(png_bytes).decode('ascii')
        return f"data:image/png;base64,{png_base64}"
    except Exception as e:
        print(f"[QRCODE PNG] Erro ao gerar QR Code PNG: {e}")
        return ""

def gerar_qrcode_pix_cpf_simples(cpf: str, nome: str = "Cliente", cidade: str = "São Paulo", valor: float = 0.0) -> str:
    """Conveniência para gerar um QR Code PIX a partir apenas do número do CPF.

    O CPF é usado como chave Pix; os demais campos (nome, cidade e valor)
    são preenchidos com valores padrão, mas o payload completo segue o
    padrão EMVCo, garantindo que o QR Code seja aceito pelos aplicativos
    de pagamento.
    """
    # Import dentro da função para evitar dependências circulares.
    from database import gerar_pix_copia_e_cola

    # Monta o payload completo (inclui a tag da chave, nome, cidade etc.).
    payload = gerar_pix_copia_e_cola(cpf, nome, cidade, valor)
    # Converte para PNG base64 usando a função já existente.
    return gerar_qrcode_pix_png_base64(payload)

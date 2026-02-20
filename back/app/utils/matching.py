import re
from typing import Optional, Tuple, Dict, List
from rapidfuzz import fuzz

from app.config import (
    FUZZY_THRESHOLD_DEFAULT,
    FUZZY_THRESHOLD_MANY_CANDIDATES,
    MANY_CANDIDATES_N,
)
from app.utils.normalizers import normalizar_material, codigo_sin_ceros, normalizar_desc

import re

def normalizar_sku_6(sku: str) -> str:
    if sku is None:
        return ""

    sku = str(sku).strip().upper()

    # Eliminar prefijo ET
    sku = re.sub(r'^ET', '', sku)

    # Eliminar sufijo letras (sin importar mayúsculas/minúsculas)
    sku = re.sub(r'[A-Z]+$', '', sku)

    # Si queda numérico → ajustar a 6 caracteres
    if sku.isdigit():
        if len(sku) > 6:
            sku = sku[:6]
        return sku.zfill(6)

    return sku

def limpiar_sku_excel(valor):
    if valor is None:
        return ""

    # Si es float real
    if isinstance(valor, float):
        valor = int(valor)

    valor = str(valor).strip()

    # Eliminar .0 si quedó
    if valor.endswith(".0"):
        valor = valor[:-2]

    return normalizar_sku_6(valor)


def encontrar_material_en_stock(
    material_pedido: str,
    desc_pedido: str,
    materiales_stock: set,
    desc_stock_por_material: dict,
):
    """
    Busca match exacto usando SKU normalizado.
    """

    material_norm = normalizar_sku_6(material_pedido)

    # Match exacto O(1)



    if material_norm in materiales_stock:
        return material_norm, {"tipo_match": "exacto"}

    return None, {"tipo_match": "no_encontrado"}


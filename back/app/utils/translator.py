# app/utils/translator.py
import json
from pathlib import Path
from typing import Optional, Dict

# Diccionarios globales en memoria para búsquedas instantáneas
_TRUCK_TO_SAP: Dict[str, dict] = {}
_SAP_TO_TRUCK: Dict[str, dict] = {}

def inicializar_traductor():
    """Carga el JSON en memoria y genera los índices bidireccionales."""
    global _TRUCK_TO_SAP, _SAP_TO_TRUCK
    if _TRUCK_TO_SAP:
        return

    ruta_json = Path(__file__).resolve().parents[3] / "data" / "codigos_sap_truck.json"

    try:
        with ruta_json.open("r", encoding="utf-8") as f:
            datos = json.load(f)

        for item in datos:
            sap = str(item["sap"]).strip()
            truck = str(item["truck"]).strip()
            _TRUCK_TO_SAP[truck] = item
            _SAP_TO_TRUCK[sap] = item
    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo de traducción en {ruta_json}")

def traducir_codigo(codigo: str) -> Optional[dict]:
    """
    Busca un código sin importar si es de SAP o de TRUCK.
    Devuelve un diccionario con {'sap', 'truck', 'descripcion'} o None.
    """
    inicializar_traductor()
    cod_limpio = str(codigo).strip()
    
    # 1. Intentar buscar como código Truck
    if cod_limpio in _TRUCK_TO_SAP:
        return _TRUCK_TO_SAP[cod_limpio]
        
    # 2. Intentar buscar como código SAP
    if cod_limpio in _SAP_TO_TRUCK:
        return _SAP_TO_TRUCK[cod_limpio]
        
    # 3. Intentar buscar rellenando con ceros a la izquierda (por si SAP viene sin ceros)
    if cod_limpio.isdigit():
        sap_con_ceros = cod_limpio.zfill(6)
        if sap_con_ceros in _SAP_TO_TRUCK:
            return _SAP_TO_TRUCK[sap_con_ceros]

    return None
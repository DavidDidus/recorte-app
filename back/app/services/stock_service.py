# app/services/stock_service.py (o la ruta que uses)
from typing import Tuple, List, Dict
import pandas as pd

from app.utils.excel import limpiar_columnas, encontrar_columna
from app.utils.translator import traducir_codigo

def clasificar_centro(centro) -> str:
    """Clasificación integrada (antiguamente en normalizers.py)"""
    centro_str = str(centro).strip()
    if centro_str.endswith("6"):
        return "bodega_principal"
    elif centro_str.endswith("7"):
        return "bodega_externa"
    return "otros"

def preparar_pedidos(df_pedidos: pd.DataFrame) -> pd.DataFrame:
    df = limpiar_columnas(df_pedidos)

    col_prod = encontrar_columna(df, candidatos_exactos=("Producto",), contiene=("producto", "material", "sku", "cod"))
    col_cnt = encontrar_columna(df, candidatos_exactos=("Cnt.Pedidos", "Cnt Pedidos", "Cnt.Pedido", "Cantidad"), contiene=("cnt", "pedido", "pedidos", "cantidad"))
    col_desc = encontrar_columna(df, candidatos_exactos=("Desc.Reducida", "Desc Reducida", "Descripción", "Descripcion"), contiene=("desc", "descrip", "nombre"))

    if not col_prod or not col_cnt:
        raise KeyError(f"Pedidos: no encontré columnas. Columnas detectadas: {list(df.columns)}")

    cols = [col_prod, col_cnt] + ([col_desc] if col_desc else [])
    df = df[cols].copy()

    rename_map = {col_prod: "Producto", col_cnt: "Cnt.Pedidos"}
    if col_desc:
        rename_map[col_desc] = "NombreProducto"
    df = df.rename(columns=rename_map)

    # NUEVO: Convertir a string limpio quitando posibles decimales de Excel (.0)
    df["Producto"] = df["Producto"].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    df["Cnt.Pedidos"] = pd.to_numeric(df["Cnt.Pedidos"], errors="coerce").fillna(0).astype(int)

    if "NombreProducto" not in df.columns:
        df["NombreProducto"] = ""

    def first_non_empty(s: pd.Series) -> str:
        s = s.astype(str).str.strip()
        s = s[s != ""]
        return s.iloc[0] if len(s) else ""

    out = df.groupby("Producto", as_index=False).agg({"Cnt.Pedidos": "sum", "NombreProducto": first_non_empty})
    return out

def preparar_stock(df_stock: pd.DataFrame) -> pd.DataFrame:
    df = limpiar_columnas(df_stock)

    col_mat = encontrar_columna(df, candidatos_exactos=("Material",), contiene=("material", "producto", "sku", "cod"))
    col_cen = encontrar_columna(df, candidatos_exactos=("Centro",), contiene=("centro", "werks"))
    col_lib = encontrar_columna(df, candidatos_exactos=("Libre utilización", "Libre utilizacion"), contiene=("libre", "utiliz", "dispon"))

    if not col_mat or not col_cen or not col_lib:
        raise KeyError(f"Stock: no encontré columnas. Columnas detectadas: {list(df.columns)}")

    df = df[[col_mat, col_cen, col_lib]].copy()
    df = df.rename(columns={col_mat: "Material", col_cen: "Centro", col_lib: "Libre_utilizacion"})

    # Traducir o estandarizar el material del Stock a su contraparte oficial en SAP usando el diccionario
    # Esto asegura que si el stock viene con SKU Truck o SAP erróneo, se homologue al código SAP oficial
    def homologar_a_sap(val):
        val_str = str(val).strip().replace(".0", "")
        traduccion = traducir_codigo(val_str)
        return traduccion["sap"] if traduccion else val_str

    df["Material"] = df["Material"].apply(homologar_a_sap)
    df["Centro"] = pd.to_numeric(df["Centro"], errors="coerce").astype("Int64")
    
    df["Libre_utilizacion"] = df["Libre_utilizacion"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    df["Libre_utilizacion"] = pd.to_numeric(df["Libre_utilizacion"], errors="coerce").fillna(0)

    # Agrupar stock consolidado
    df_stock_agg = df.groupby(["Material", "Centro"], as_index=False)["Libre_utilizacion"].sum()
    return df_stock_agg

def obtener_stock_por_tipo(df_stock: pd.DataFrame, material_sap: str) -> dict:
    filas = df_stock[df_stock["Material"] == material_sap]

    if filas.empty:
        return {"bodega_principal": 0, "bodega_externa": 0, "otros": 0, "detalle_centros": {}}

    detalle = {}
    for centro, stock in filas.groupby("Centro")["Libre_utilizacion"].sum().items():
        if pd.isna(centro): continue
        detalle[str(int(centro))] = float(stock)

    sp = se = so = 0.0
    for centro, stock in detalle.items():
        tipo = clasificar_centro(centro)
        if tipo == "bodega_principal": sp += stock
        elif tipo == "bodega_externa": se += stock
        else: so += stock

    return {"bodega_principal": sp, "bodega_externa": se, "otros": so, "detalle_centros": detalle}

def evaluar_producto_por_tipo(material, nombre, pedidos, stock_tipos, existe_material):
    pedidos = int(pedidos)
    sp = float(stock_tipos["bodega_principal"])
    se = float(stock_tipos["bodega_externa"])

    asigna_principal = min(pedidos, sp)
    restante = pedidos - asigna_principal
    asigna_externa = min(restante, se)
    faltante = pedidos - asigna_principal - asigna_externa

    if pedidos == 0:
        estado = "Sin demanda"
    elif not existe_material:
        estado = "AVISO - Código no existe en catálogo maestro"
    elif faltante == 0 and asigna_externa > 0:
        estado = f"OK - Completa con bodega externa ({asigna_externa} cajas)"
    elif asigna_principal == pedidos:
        estado = "OK - Stock completo en bodega principal"
    elif sp + se == 0:
        estado = "NO - Sin stock"
    else:
        estado = "NO - Stock insuficiente"

    return {
        "Producto": material,
        "NombreProducto": str(nombre),
        "Pedidos": pedidos,
        "Stock_Bodega_Principal": sp,
        "Stock_Bodega_Externa": se,
        "Asignado_Principal": asigna_principal,
        "Asignado_Externa": asigna_externa,
        "Faltante": faltante,
        "Estado": estado,
    }

def procesar_validacion(df_pedidos_raw: pd.DataFrame, df_stock_raw: pd.DataFrame):
    df_pedidos = preparar_pedidos(df_pedidos_raw)
    df_stock = preparar_stock(df_stock_raw)

    resultados = []
    for _, row in df_pedidos.iterrows():
        material_pedido = row["Producto"]
        pedidos = int(row["Cnt.Pedidos"])
        nombre = row.get("NombreProducto", "")

        # NUEVO: Intentamos traducir el código de la orden de pedido
        traduccion = traducir_codigo(material_pedido)

        if not traduccion:
            # Si el código no está en el JSON maestro
            resultados.append({
                "Producto": material_pedido,
                "NombreProducto": str(nombre),
                "Pedidos": pedidos,
                "Faltante": pedidos,
                "Estado": "AVISO - Código no reconocido en traductor",
            })
            continue

        # Usamos siempre la clave 'sap' unificada para contrastar contra el Dataframe de Stock
        codigo_sap = traduccion["sap"]
        # Si el pedido no traía descripción, usamos la del JSON maestro
        if not nombre:
            nombre = traduccion["descripcion"]

        stock_tipos = obtener_stock_por_tipo(df_stock, codigo_sap)
        
        resultados.append(
            evaluar_producto_por_tipo(
                material=material_pedido, # Mantiene el código original ingresado por el usuario
                nombre=nombre,
                pedidos=pedidos,
                stock_tipos=stock_tipos,
                existe_material=True
            )
        )

    return resultados, df_pedidos, df_stock
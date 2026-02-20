import { useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE;

export default function App() {
  const [file, setFile] = useState(null);

  const [sheets, setSheets] = useState([]);
  const [hojaPedidos, setHojaPedidos] = useState("");
  const [hojaStock, setHojaStock] = useState("");

  const [loadingSheets, setLoadingSheets] = useState(false);
  const [loadingCalc, setLoadingCalc] = useState(false);

  const [error, setError] = useState("");
  const [resultados, setResultados] = useState([]);
  const [filtroEstado, setFiltroEstado] = useState("Todos");

  const columnasFijas = useMemo(() => {
  if (filtroEstado === "AVISO - No se encontró match confiable en stock") {
    return [
      "Producto",
      "NombreProducto",
      "Pedidos",
      "Estado",
    ];
  } else {
    return [
      "Producto",
      "NombreProducto",
      "Pedidos",
      "Stock_Bodega_Principal",
      "Stock_Bodega_Externa",
      "Estado",
    ];
  }
}, [filtroEstado]);

  const estadosDisponibles = useMemo(() => {
  if (!resultados?.length) return [];
  const estados = [...new Set(resultados.map((r) => r.EstadoBase))];
  return estados.sort();
}, [resultados]);


  const resultadosFiltrados = useMemo(() => {
    if (filtroEstado === "Todos") return resultados;
    return resultados.filter((r) => r.EstadoBase === filtroEstado);
  }, [resultados, filtroEstado]);

  function guessDefaultSheets(list) {
    const lower = list.map((s) => s.toLowerCase());

    const pickPedidos =
      list[lower.findIndex((s) => s.includes("hoja1"))] ||
      list[lower.findIndex((s) => s.includes("pedido"))] ||
      list[0] ||
      "";

    const pickStock =
      list[lower.findIndex((s) => s.includes("data"))] ||
      list[lower.findIndex((s) => s.includes("stock"))] ||
      list[1] ||
      list[0] ||
      "";

    return { pickPedidos, pickStock };
  }

  async function fetchSheets(selectedFile) {
    setError("");
    setResultados([]);
    setSheets([]);
    setHojaPedidos("");
    setHojaStock("");

    if (!selectedFile) return;

    setLoadingSheets(true);
    try {
      const form = new FormData();
      form.append("file", selectedFile);

      const sheetsEndpoint = API_BASE ? `${API_BASE.replace(/\/$/, "")}/api/sheets` : `/api/sheets`;
      const res = await fetch(sheetsEndpoint, {
        method: "POST",
        body: form,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Error obteniendo hojas");

      const list = data.sheets || [];
      setSheets(list);

      const { pickPedidos, pickStock } = guessDefaultSheets(list);
      setHojaPedidos(pickPedidos);
      setHojaStock(pickStock);
    } catch (err) {
      setError(err.message || "Error");
    } finally {
      setLoadingSheets(false);
    }
  }

  async function handleFileChange(e) {
    const f = e.target.files?.[0] || null;
    setFile(f);
    await fetchSheets(f);
  }

  async function handleCalcular(e) {
    e.preventDefault();
    setError("");
    setResultados([]);
    setFiltroEstado("Todos");

    if (!file) {
      setError("Selecciona un archivo Excel.");
      return;
    }
    if (!hojaPedidos || !hojaStock) {
      setError("Selecciona la hoja de Pedidos y la hoja de Stock.");
      return;
    }

    setLoadingCalc(true);
    try {
      const form = new FormData();
      form.append("file", file);

      // Build endpoint safely: use absolute API_BASE if provided, otherwise use relative path.
      const endpoint = API_BASE ? `${API_BASE.replace(/\/$/, "")}/api/validar-stock` : `/api/validar-stock`;
      const params = new URLSearchParams({ hoja_pedidos: hojaPedidos, hoja_stock: hojaStock });

      const res = await fetch(`${endpoint}?${params.toString()}`, {
        method: "POST",
        body: form,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Error al validar stock");


      const resultadosConEstadoBase = (data.resultados || []).map((r) => {
      const estado = r.Estado;

      let estadoBase = estado;

      // Si contiene "(x cajas)" lo quitamos para el filtro
      if (estado.startsWith("OK - Completa con bodega externa")) {
        estadoBase = "OK - Completa con bodega externa";
      }

      return {
        ...r,
        EstadoBase: estadoBase, // se usará para filtrar
      };
    });

    setResultados(resultadosConEstadoBase);

    } catch (err) {
      setError(err.message || "Error");
    } finally {
      setLoadingCalc(false);
    }
  }

  return (
    <div style={{ maxWidth: 1100, margin: "40px auto", fontFamily: "system-ui" }}>
      <h2>Calculo Recorte</h2>

      <div style={{ display: "grid", gap: 12 }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Excel</span>
          <input type="file" accept=".xlsx,.xls" onChange={handleFileChange} />
        </label>

        {loadingSheets && <div>Detectando hojas...</div>}

        {sheets.length > 0 && (
          <form onSubmit={handleCalcular} style={{ display: "grid", gap: 12 }}>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>

              <label style={{ display: "grid", gap: 6 }}>
                <span>Hoja Stock</span>
                <select value={hojaStock} onChange={(e) => setHojaStock(e.target.value)}>
                  <option value="">Selecciona...</option>
                  {sheets.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
              
              <label style={{ display: "grid", gap: 6 }}>
                <span>Hoja Recorte</span>
                <select value={hojaPedidos} onChange={(e) => setHojaPedidos(e.target.value)}>
                  <option value="">Selecciona...</option>
                  {sheets.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <button disabled={loadingCalc}>
              {loadingCalc ? "Procesando..." : "Calcular"}
            </button>
          </form>
        )}

        {error && <p style={{ color: "crimson" }}>{error}</p>}

        {!!resultados.length && (
          <div style={{ marginTop: 16 }}>
            <div style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
              <label style={{ fontWeight: "600" }}>Filtrar por estado:</label>
              <select
                value={filtroEstado}
                onChange={(e) => setFiltroEstado(e.target.value)}
                style={{ padding: "6px 10px", borderRadius: "4px", border: "1px solid #ccc" }}
              >
                <option value="Todos">Todos ({resultados.length})</option>
                {estadosDisponibles.map((estado) => {
                  const count = resultados.filter((r) => r.EstadoBase === estado).length;
                  return (
                    <option key={estado} value={estado}>
                      {estado} ({count})
                    </option>
                  );
                })}
              </select>
            </div>

            <div style={{ overflowX: "auto" }}>
              <table border="1" cellPadding="8" style={{ borderCollapse: "collapse", width: "100%" }}>
                <thead>
                  <tr>
                    {columnasFijas.map((c) => (
                      <th key={c} style={{ textAlign: "left", whiteSpace: "nowrap" }}>
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {resultadosFiltrados.map((row, idx) => (
                    <tr key={idx}>
                      {columnasFijas.map((c) => (
                        <td key={c} style={{ whiteSpace: "nowrap" }}>
                          {String(row[c] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {resultadosFiltrados.length === 0 && (
              <p style={{ color: "#666", marginTop: 12 }}>
                No hay resultados para el estado seleccionado.
              </p>
            )}
          </div>
        )}

        {!error && !loadingCalc && resultados.length === 0 && sheets.length === 0 && (
          <p style={{ color: "#666" }}>Sube un Excel para detectar las hojas.</p>
        )}
      </div>
    </div>
  );
}
